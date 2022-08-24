import base64
import qrcode
from barcode import Code128
from barcode.writer import SVGWriter
from datetime import datetime
from random import randint
from io import BytesIO
from typing import Type
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError
from tortoise import exceptions
from tortoise.transactions import atomic
from tortoise.queryset import Q
from pydantic import BaseModel

import settings
from core.communication.event import NotifyVisitorInBlackListEvent
from core.dto.access import EntityId
from core.dto.service import (VisitorDto,
                              PassportDto,
                              MilitaryIdDto,
                              VisitSessionDto,
                              DriveLicenseDto,
                              PassDto,
                              TransportDto,
                              VisitorPhotoDto,
                              WaterMarkDto,
                              InternationalPassportDto)
from infrastructure.database.repository import EntityRepository
from infrastructure.database.models import (Passport,
                                            Pass,
                                            DriveLicense,
                                            MilitaryId,
                                            Transport,
                                            Visitor,
                                            VisitSession,
                                            VisitorPhoto,
                                            Claim,
                                            BlackList,
                                            WaterMark,
                                            InternationalPassport,
                                            WatermarkPosition,
                                            ClaimWay,
                                            SystemUser,
                                            StrangerThings,
                                            PushSubscription,
                                            MODEL)
from application.exceptions import InconsistencyError
from application.service.web_push import WebPushController
from application.service.base_service import BaseService
from application.service.claim import ClaimService
from application.service.black_list import BlackListService
from core.plugins.plugins_wrap import AddPlugins


class VisitorService(BaseService):
    target_model = Visitor

    @staticmethod
    async def get_visitor_fk_relations(
            dto: VisitorDto.CreationDto | VisitorDto.UpdateDto
    ) -> dict[str, Type[MODEL] | None]:
        """Trying to get Visitor's documents, transports, claims and returning them as a dict"""
        fk_relations = {
            "passport": await Passport.get_or_none(id=dto.passport) if dto.passport else None,
            "international_passport": await InternationalPassport.get_or_none(id=dto.international_passport)
            if dto.international_passport else None,
            "pass_id": await Pass.get_or_none(id=dto.pass_id) if dto.pass_id else None,
            "drive_license": await DriveLicense.get_or_none(id=dto.drive_license) if dto.drive_license else None,
            "military_id": await MilitaryId.get_or_none(id=dto.military_id) if dto.military_id else None,
            "transport": await Transport.get_or_none(id=dto.transport) if dto.transport else None,
            "claim": await Claim.get_or_none(id=dto.claim).prefetch_related() if dto.claim else None,
            "visitor_photo": await VisitorPhoto.get_or_none(id=dto.visitor_photo) if dto.visitor_photo else None
        }
        return fk_relations

    @atomic(settings.CONNECTION_NAME)
    async def create(self, system_user: SystemUser, dto: VisitorDto.CreationDto) -> Visitor:
        try:
            if await Visitor.exists(
                    Q(passport=dto.passport) |
                    Q(international_passport=dto.international_passport) |
                    Q(drive_license=dto.drive_license) |
                    Q(military_id=dto.military_id),
                    deleted=False
            ):
                raise InconsistencyError(message="This visitor already exists.")

            fk_relations = await self.get_visitor_fk_relations(dto)

            entity_kwargs = {
                field: value for field, value in dto.dict().items()
                if not (field in fk_relations or "date" in field)
            }
            date_of_birth = visit_start_date = visit_end_date = None

            if dto.date_of_birth:
                date_of_birth = datetime.strptime(dto.date_of_birth, settings.DATE_FORMAT)
            if dto.visit_start_date:
                visit_start_date = datetime.strptime(dto.visit_start_date, settings.DATETIME_FORMAT).astimezone()
            if dto.visit_end_date:
                visit_end_date = datetime.strptime(dto.visit_end_date, settings.DATETIME_FORMAT).astimezone()

            visitor = await Visitor.create(**entity_kwargs,
                                           **fk_relations,
                                           date_of_birth=date_of_birth,
                                           visit_start_date=visit_start_date,
                                           visit_end_date=visit_end_date)

            visitor_in_black_list = await BlackList.exists(visitor=visitor)
            if visitor_in_black_list:
                self.notify(NotifyVisitorInBlackListEvent(
                    await BlackListService.collect_target_users(visitor, user=system_user)))

            if claim := fk_relations["claim"]:
                claim_way = await ClaimWay.get_or_none(claims=claim.id).prefetch_related(
                    "system_users") if claim.claim_way else None
                if claim_way:
                    self.notify(await ClaimService.EventName.time_before_for_claim_way(claim_way, claim))

            return visitor

        except exceptions.IntegrityError as ex:
            raise InconsistencyError(ex=ex)

    @atomic(settings.CONNECTION_NAME)
    async def update(self, system_user: SystemUser, entity_id: EntityId, dto: VisitorDto.UpdateDto) -> Visitor:
        visitor = await Visitor.get_or_none(id=entity_id).prefetch_related("visit_session")
        if visitor is None:
            raise InconsistencyError(message=f"Visitor with id={entity_id} does not exist.")

        visitor_in_black_list = await BlackList.exists(visitor=visitor)
        if visitor_in_black_list:
            self.notify(
                NotifyVisitorInBlackListEvent(await BlackListService.collect_target_users(visitor, user=system_user)))

        fk_relations = await self.get_visitor_fk_relations(dto)

        await self.check_for_suspicious_actions(system_user, visitor, dto, visitor_in_black_list)

        try:
            for field, value in dto.dict().items():
                if value:
                    if field == "pass_id" and visitor_in_black_list:
                        raise InconsistencyError(message=f"Visitor with id={entity_id} is in BlackList")

                    if field in fk_relations:
                        setattr(visitor, field, fk_relations.get(field))

                    elif field.startswith("date"):
                        setattr(visitor, field, datetime.strptime(value, settings.DATE_FORMAT))

                    elif field.endswith("date"):
                        setattr(visitor, field, datetime.strptime(value, settings.DATETIME_FORMAT))
                    else:
                        setattr(visitor, field, value)

            await visitor.save()

            if claim := fk_relations["claim"]:
                claim_way = await ClaimWay.get_or_none(id=claim.claim_way_id).prefetch_related(
                    "system_users") if claim.claim_way else None
                if claim_way:
                    self.notify(await ClaimService.EventName.time_before_for_claim_way(claim_way, claim))

            if fk_relations["pass_id"] and visitor.claim:
                await self.send_webpush(system_user, visitor)

            return visitor

        except exceptions.IntegrityError as ex:
            raise InconsistencyError(message=f"{ex}")

    async def send_webpush(self, system_user: SystemUser, visitor: Visitor) -> None:
        """
        Send webpush notification to claim creator
        if pass was assigned to visitor another system_user
        """
        claim = await Claim.get(id=visitor.claim_id)  # noqa
        if claim.system_user_id != system_user.id:  # noqa
            title = f"Выдан пропуск для {visitor}."
            body = f"{system_user} назначил пропуск №{visitor.pass_id} посетителю {visitor}."
            subscriptions = await PushSubscription.filter(system_user=claim.system_user_id)  # noqa
            await WebPushController.trigger_push_notifications_for_subscriptions(subscriptions, title, body)

    @atomic(settings.CONNECTION_NAME)
    async def delete(self, system_user: SystemUser, entity_id: EntityId) -> EntityId:
        await EntityRepository.check_not_exist_or_delete(Visitor, entity_id)
        await Visitor.filter(id=entity_id).update(deleted=True)
        return entity_id

    @staticmethod
    async def check_for_suspicious_actions(system_user: SystemUser, visitor: Visitor,
                                           dto: VisitorDto.UpdateDto, visitor_in_blacklist: bool) -> None:
        """Check for "suspicious" actions and save it to StrangerThings."""
        if visitor.pass_id and any((dto.first_name, dto.last_name, dto.middle_name)):
            # If changing FIO after pass_id has been assigned, save this event
            dct = {"before": await visitor.values_dict(),
                   "after": {key: value for key, value in dto.dict().items()
                             if key in ("first_name", "last_name", "middle_name") and value}}
            await StrangerThings.create(system_user=system_user, fio_changed=dct)

        if end_visit := await VisitSession.filter(visitor=visitor.id).order_by("-exit").first():
            # If changing Visitor data after visit, save this event
            time_now = datetime.now().astimezone()
            if end_visit.exit and time_now > end_visit.exit:
                dct = {"before": await visitor.values_dict(),
                       "after": {key: value for key, value in dto.dict().items() if value}}
                await StrangerThings.create(system_user=system_user, data_changed=dct)

        if visitor_in_blacklist:
            dct = {"visitor": await visitor.values_dict(), "visitor_in_blacklist": visitor_in_blacklist}
            await StrangerThings.create(system_user=system_user, pass_to_black_list=dct)

    @staticmethod
    async def get_info_about_current_visit(entity_id: EntityId) -> dict[str, dict | list[dict] | str | None]:
        """Return info about visitor's visit"""
        visitor: Visitor = await Visitor.get_or_none(id=entity_id).prefetch_related("visit_session")
        if visitor is None:
            raise InconsistencyError(message=f"Visitor with id={entity_id} doesn't exist.")

        visit_info = {
            "pass": await Pass.filter(visitor=entity_id).values() if visitor.pass_id else None,
            "visit_info": await VisitSession.filter(visitor=visitor.id).values("enter", "exit")
            if visitor.visit_session else None,
            "who_invited": visitor.who_invited,
            "destination": visitor.destination,
            "documents": {
                "passport": await Passport.filter(visitor=entity_id).values()
                if visitor.passport else None,
                "international_passport": await InternationalPassport.filter(visitor=entity_id).values()
                if visitor.international_passport else None,
                "drive_license": await DriveLicense.filter(visitor=entity_id).values()
                if visitor.drive_license else None,
                "military_id": await MilitaryId.filter(visitor=entity_id).values()
                if visitor.military_id else None,
            }
        }
        # visit_info = await visitor.values_dict(m2m_fields=True, fk_fields=True, backward_fk_fields=True,
        #                                        o2o_fields=True)

        return visit_info


class PassportService(BaseService):
    target_model = Passport

    @atomic(settings.CONNECTION_NAME)
    async def create(self, system_user: SystemUser, dto: PassportDto.CreationDto) -> Passport:
        already_exists = await Passport.exists(number=dto.number)
        if already_exists:
            raise InconsistencyError(message=f"Passport with number={dto.number} already exists.")
        kwrgs = await set_params_for_document(dto)

        passport = await Passport.create(**kwrgs)

        return passport

    @atomic(settings.CONNECTION_NAME)
    async def update(self, system_user: SystemUser, entity_id: EntityId, dto: PassportDto.UpdateDto) -> Passport:
        passport = await Passport.get_or_none(id=entity_id)
        if passport is None:
            raise InconsistencyError(message=f"Passport with id={entity_id} does not exist.")

        await set_params_for_document(dto, passport)

        await passport.save()
        return passport

    @atomic(settings.CONNECTION_NAME)
    async def delete(self, system_user: SystemUser, entity_id: EntityId) -> EntityId:
        return await super().delete(system_user, entity_id)


class InternationalPassportService(BaseService):
    target_model = InternationalPassport

    @atomic(settings.CONNECTION_NAME)
    async def create(self, system_user: SystemUser, dto: InternationalPassportDto.CreationDto) -> InternationalPassport:
        already_exists = await InternationalPassport.exists(number=dto.number)
        if already_exists:
            raise InconsistencyError(message=f"InternationalPassport with number={dto.number} already exists.")
        kwrgs = await set_params_for_document(dto)

        international_passport = await InternationalPassport.create(**kwrgs)

        return international_passport

    @atomic(settings.CONNECTION_NAME)
    async def update(self, system_user: SystemUser, entity_id: EntityId,
                     dto: InternationalPassportDto.UpdateDto) -> InternationalPassport:
        international_passport = await InternationalPassport.get_or_none(id=entity_id)
        if international_passport is None:
            raise InconsistencyError(message=f"InternationalPassport with id={entity_id} does not exist.")

        await set_params_for_document(dto, international_passport)

        await international_passport.save()
        return international_passport

    @atomic(settings.CONNECTION_NAME)
    async def delete(self, system_user: SystemUser, entity_id: EntityId) -> EntityId:
        return await super().delete(system_user, entity_id)


class MilitaryIdService(BaseService):
    target_model = MilitaryId

    @atomic(settings.CONNECTION_NAME)
    async def create(self, system_user: SystemUser, dto: MilitaryIdDto.CreationDto) -> MilitaryId:
        already_exists = await MilitaryId.exists(number=dto.number)
        if already_exists:
            raise InconsistencyError(message=f"MilitaryId with number={dto.number} already exists.")
        kwrgs = await set_params_for_document(dto)

        military_id = await MilitaryId.create(**kwrgs)

        return military_id

    @atomic(settings.CONNECTION_NAME)
    async def update(self, system_user: SystemUser, entity_id: EntityId, dto: MilitaryIdDto.UpdateDto) -> MilitaryId:
        military_id = await MilitaryId.get_or_none(id=entity_id)
        if military_id is None:
            raise InconsistencyError(message=f"MilitaryId with id={entity_id} does not exist.")

        await set_params_for_document(dto, military_id)

        await military_id.save()
        return military_id

    @atomic(settings.CONNECTION_NAME)
    async def delete(self, system_user: SystemUser, entity_id: EntityId) -> EntityId:
        return await super().delete(system_user, entity_id)


class DriveLicenseService(BaseService):
    target_model = DriveLicense

    @atomic(settings.CONNECTION_NAME)
    async def create(self, system_user: SystemUser, dto: DriveLicenseDto.CreationDto) -> DriveLicense:
        already_exists = await DriveLicense.exists(number=dto.number)
        if already_exists:
            raise InconsistencyError(message=f"DriveLicense with number={dto.number} already exists.")

        kwrgs = await set_params_for_document(dto)

        drive_license = await DriveLicense.create(**kwrgs)

        return drive_license

    @atomic(settings.CONNECTION_NAME)
    async def update(self, system_user: SystemUser, entity_id: EntityId,
                     dto: DriveLicenseDto.UpdateDto) -> DriveLicense:
        drive_license = await DriveLicense.get_or_none(id=entity_id)
        if drive_license is None:
            raise InconsistencyError(message=f"DriveLicense with id={entity_id} does not exist.")

        await set_params_for_document(dto, drive_license)

        await drive_license.save()
        return drive_license

    @atomic(settings.CONNECTION_NAME)
    async def delete(self, system_user: SystemUser, entity_id: EntityId) -> EntityId:
        return await super().delete(system_user, entity_id)


class VisitSessionService(BaseService):
    target_model = VisitSession

    @atomic(settings.CONNECTION_NAME)
    async def create(self, system_user: SystemUser, dto: VisitSessionDto.CreationDto) -> VisitSession:

        visitor = await Visitor.get_or_none(id=dto.visitor)
        if visitor is None:
            raise InconsistencyError(message=f"There is no visitor with id={dto.visitor}. "
                                             f"You should provide valid Visitor to create VisitSession.")

        entity_kwargs = {field: datetime.strptime(value, settings.DATETIME_FORMAT).astimezone()
                         for field, value in dto.dict().items()
                         if value and field != "visitor"}

        visit_session = await VisitSession.create(**entity_kwargs, visitor=visitor)
        return visit_session

    @atomic(settings.CONNECTION_NAME)
    async def update(self, system_user: SystemUser, entity_id: EntityId,
                     dto: VisitSessionDto.UpdateDto) -> VisitSession:
        visit_session = await VisitSession.get_or_none(id=entity_id)
        if visit_session is None:
            raise InconsistencyError(message=f"VisitSession with id={entity_id} does not exist.")

        for field, value in dto.dict().items():
            if value:
                setattr(visit_session, field, datetime.strptime(value, settings.DATETIME_FORMAT))

        await visit_session.save()
        return visit_session

    @atomic(settings.CONNECTION_NAME)
    async def delete(self, system_user: SystemUser, entity_id: EntityId) -> EntityId:
        return await super().delete(system_user, entity_id)


class VisitorPhotoService(BaseService):
    target_model = VisitorPhoto

    @atomic(settings.CONNECTION_NAME)
    async def create(self, system_user: SystemUser, dto: VisitorPhotoDto.CreationDto) -> VisitorPhoto:

        if any((dto.webcam_img, dto.scan_img, dto.car_number_img)):
            await self.work_with_images(dto)

        visitor_photo = await VisitorPhoto.create(**dto.dict())

        return visitor_photo

    @atomic(settings.CONNECTION_NAME)
    async def update(self, system_user: SystemUser, entity_id: EntityId,
                     dto: VisitorPhotoDto.UpdateDto) -> VisitorPhoto:
        visitor_photo = await VisitorPhoto.get_or_none(id=entity_id)
        if visitor_photo is None:
            raise InconsistencyError(message=f"VisitorPhoto with id={entity_id} does not exist.")

        if any((dto.webcam_img, dto.scan_img, dto.car_number_img)):
            await self.work_with_images(dto)

        entity_kwargs = {field: value for field, value in dto.dict().items() if value}

        await visitor_photo.update_from_dict({**entity_kwargs})
        await visitor_photo.save()
        return visitor_photo

    @atomic(settings.CONNECTION_NAME)
    async def delete(self, system_user: SystemUser, entity_id: EntityId) -> EntityId:
        return await super().delete(system_user, entity_id)

    async def work_with_images(self, dto: VisitorPhotoDto.CreationDto | VisitorPhotoDto.UpdateDto) -> None:
        """
        If watermark is True -> applying watermark to images
        and then convert them to byte string with separator
        """
        if dto.add_watermark_image:
            await WaterMarkService.apply_watermark(dto, w_type="image")

        if dto.add_watermark_text:
            await WaterMarkService.apply_watermark(dto, w_type="text")

        await self.convert_list_img_to_byte_string(dto)

    @staticmethod
    async def convert_list_img_to_byte_string(dto: VisitorPhotoDto.CreationDto | VisitorPhotoDto.UpdateDto) -> None:
        """Receive images as list of bytes and convert it to byte string with separator"""
        separator = b"$"
        max_photo_to_upload: int = await settings.system_settings("max_photo_upload")

        for field, value in dto.dict().items():
            if value:
                if isinstance(value, list):
                    if len(value) > max_photo_to_upload:
                        raise InconsistencyError(message=f"You can't upload more than {max_photo_to_upload} images.")
                    setattr(dto, field, separator.join(value))
                elif field.startswith("add_"):
                    setattr(dto, field, False)


class PassService(BaseService):
    target_model = Pass

    @atomic(settings.CONNECTION_NAME)
    async def create(self, system_user: SystemUser, dto: PassDto.CreationDto) -> Pass:
        if not dto.rfid:  # TODO who will provide rfid?
            setattr(dto, "rfid", randint(10 ** 6, 10 ** 7 - 1))
        entity_kwargs = {field: value
                         for field, value in dto.dict().items()
                         if value and not field.startswith("valid")}

        valid_till_date = datetime.strptime(dto.valid_till_date, settings.DATETIME_FORMAT).astimezone()

        visitor_pass = await Pass.create(**entity_kwargs,
                                         valid_till_date=valid_till_date,
                                         valid=False if dto.valid is False else True)
        return visitor_pass

    @atomic(settings.CONNECTION_NAME)
    async def update(self, system_user: SystemUser, entity_id: EntityId, dto: PassDto.UpdateDto) -> Pass:
        visitor_pass = await Pass.get_or_none(id=entity_id)
        if visitor_pass is None:
            raise InconsistencyError(message=f"Pass with id={entity_id} does not exist.")

        for field, value in dto.dict().items():
            if value:
                if field == "valid_till_date":
                    setattr(visitor_pass, field, datetime.strptime(value, settings.DATETIME_FORMAT))
                else:
                    setattr(visitor_pass, field, value)

        visitor_pass.valid = False if dto.valid is False else True

        await visitor_pass.save()
        return visitor_pass

    @atomic(settings.CONNECTION_NAME)
    async def delete(self, system_user: SystemUser, entity_id: EntityId) -> EntityId:
        return await super().delete(system_user, entity_id)

    @atomic(settings.CONNECTION_NAME)
    async def create_qr_code(self, system_user: SystemUser, entity: EntityId) -> str:
        """Creating QR code from Pass.rfid"""
        pass_id = await Pass.get_or_none(id=entity).only("rfid")
        if pass_id.rfid is None:
            raise InconsistencyError(message="To create qrcode RFID couldn't be NULL.")
        qr = qrcode.QRCode()
        qr.add_data(pass_id.rfid)
        qr.make(fit=True)
        qr = qr.make_image(fill_color="black", back_color="white")  # qrcode.image.pil.PilImage
        qr.save(buffered := BytesIO())
        image = str(base64.b64encode(buffered.getvalue()))
        buffered.close()
        return image

    @atomic(settings.CONNECTION_NAME)
    async def create_barcode(self, system_user: SystemUser, entity: EntityId) -> str:
        """Creating BAR code from Pass.rfid"""
        pass_id = await Pass.get_or_none(id=entity).only("rfid")
        if pass_id.rfid is None:
            raise InconsistencyError(message="To create barcode RFID couldn't be NULL.")
        Code128(str(pass_id.rfid), writer=SVGWriter()).write(buffered := BytesIO())
        bar_code = str(base64.b64encode(buffered.getvalue()))
        buffered.close()
        return bar_code


class TransportService(BaseService):
    target_model = Transport

    @atomic(settings.CONNECTION_NAME)
    async def create(self, system_user: SystemUser, dto: TransportDto.CreationDto) -> Transport:
        await EntityRepository.check_exist(Transport, number=dto.number)

        transport = await Transport.create(model=dto.model,
                                           number=dto.number,
                                           color=dto.color)
        claims = await Claim.filter(id__in=dto.claims)
        await transport.claims.add(*claims)

        return transport

    @atomic(settings.CONNECTION_NAME)
    async def update(self, system_user: SystemUser, entity_id: EntityId, dto: TransportDto.UpdateDto) -> Transport:
        transport = await Transport.get_or_none(id=entity_id)
        if transport is None:
            raise InconsistencyError(message=f"Transport with id={entity_id} does not exist.")

        for field, value in dto.dict().items():
            if value:
                if field == "claims":
                    claims = await Claim.filter(id__in=value)
                    await transport.claims.add(*claims)
                else:
                    setattr(transport, field, value)

        await transport.save()
        return transport

    @atomic(settings.CONNECTION_NAME)
    async def delete(self, system_user: SystemUser, entity_id: EntityId) -> EntityId:
        return await super().delete(system_user, entity_id)


class WaterMarkService(BaseService):
    target_model = WaterMark

    @atomic(settings.CONNECTION_NAME)
    async def create(self, system_user: SystemUser, dto: WaterMarkDto.CreationDto) -> MODEL:
        return await super().create(system_user, dto)

    @atomic(settings.CONNECTION_NAME)
    async def update(self, system_user: SystemUser, entity_id: EntityId, dto: TransportDto.UpdateDto) -> WaterMark:
        watermark = await WaterMark.get_or_none(id=entity_id)
        if watermark is None:
            raise InconsistencyError(message=f"WaterMark with id={entity_id} does not exist.")

        entity_kwargs = {field: value for field, value in dto.dict().items() if value}
        await watermark.update_from_dict(entity_kwargs)
        await watermark.save()
        return watermark

    @atomic(settings.CONNECTION_NAME)
    async def delete(self, system_user: SystemUser, entity_id: EntityId) -> EntityId:
        return await super().delete(system_user, entity_id)

    @staticmethod
    async def apply_watermark(dto: VisitorPhotoDto.CreationDto | VisitorPhotoDto.UpdateDto,
                              w_type: str = "image") -> None:
        """Add watermark to the images"""
        watermark = await WaterMarkService._get_watermark(w_type, dto)
        image_format: str = await settings.system_settings("watermark_format")
        if w_type == "text":
            font_size: int = await settings.system_settings("watermark_font_size")
            font_type: str = await settings.system_settings("watermark_font_type")
            font_rgb_color: tuple[int, int, int] = await settings.system_settings("watermark_font_rgb_color")

        for field, value in dto.dict().items():
            if isinstance(value, list):
                for image in value:
                    buffered = BytesIO()
                    b64image = base64.b64decode(image)
                    try:
                        with Image.open(BytesIO(b64image)) as base_image:
                            width, height = base_image.size  # In pixels
                            coordinates = await WaterMarkService._get_coordinates(width, height, dto)

                            if w_type == "image":
                                base_image.paste(watermark, coordinates, mask=watermark)

                            if w_type == "text":
                                add_text = ImageDraw.Draw(base_image)
                                my_font = ImageFont.truetype(font_type, size=font_size)  # noqa
                                # Set coordinates, text, color, font type
                                add_text.text(coordinates,
                                              watermark,
                                              fill=font_rgb_color,  # noqa
                                              font=my_font)
                            # Save the edited image
                            # base_image.show()
                            base_image.save(buffered, format=image_format, compress_level=1)
                            new_image = base64.b64encode(buffered.getvalue())
                            value = list(map(lambda x: x.replace(image, new_image), value))
                    except UnidentifiedImageError as exx:
                        raise InconsistencyError(ex=exx,
                                                 message=f"Image {image[:15] + b'...'} can't be opened and identified. "
                                                         f"Not a valid image.")
                    except AttributeError as e:
                        raise InconsistencyError(ex=e,
                                                 message=f"Not valid width={dto.watermark_width} "
                                                         f"or height={dto.watermark_height}"
                                                         f"Choose not more than watermark actual size={watermark.size}.")
                    except OSError as ex:
                        raise InconsistencyError(ex=ex, message="The file could not be written. "
                                                                "The file may have been created, "
                                                                "and may contain partial data.")
                    finally:
                        buffered.close()

                setattr(dto, field, value)

    @staticmethod
    async def _get_watermark(w_type: str,
                             dto: VisitorPhotoDto.CreationDto | VisitorPhotoDto.UpdateDto) -> Type[Image.Image] | str:
        """Get WaterMark from DB and returns Image or string object"""
        watermark_type = await WaterMark.get_or_none(id=dto.watermark_id)
        if watermark_type is None:
            raise InconsistencyError(message=f"WaterMark with id={dto.watermark_id} does not exist.")

        if w_type == "image":
            b64watermark = base64.b64decode(watermark_type.image)
            try:
                with Image.open(BytesIO(b64watermark)) as watermark:
                    if watermark.mode != "RGBA":
                        transparency: int = await settings.system_settings("watermark_transparency")
                        watermark.putalpha(transparency)
                    watermark.thumbnail((dto.watermark_width, dto.watermark_height), resample=0)  # 0=Nearest
                    return watermark
            except UnidentifiedImageError as exx:
                raise InconsistencyError(ex=exx,
                                         message=f"Image {watermark_type.image[:15] + b'...'} "
                                                 f"cannot be opened and identified.")
        if w_type == "text":
            return watermark_type.text

    @staticmethod
    async def _get_coordinates(width: int, height: int,
                               dto: VisitorPhotoDto.CreationDto | VisitorPhotoDto.UpdateDto) -> tuple[int, int]:
        """Calculate proper coordinates to position watermark on image."""
        if dto.watermark_width > width // 2:
            raise InconsistencyError(
                message=f"Watermark width={dto.watermark_width} greater than "
                        f"available image width for applying watermark."
                        f"Choose width less than {width // 2}."
            )
        if dto.watermark_height > height // 2:
            raise InconsistencyError(
                message=f"Watermark height={dto.watermark_height} greater than "
                        f"available image height for applying watermark."
                        f"Choose height less than {height // 2}."
            )
        match dto.watermark_position:
            case WatermarkPosition.UPPER_LEFT:
                return 0, 0
            case WatermarkPosition.UPPER_RIGHT:
                return width - dto.watermark_width, 0
            case WatermarkPosition.LOWER_LEFT:
                return 0, height - dto.watermark_height
            case WatermarkPosition.LOWER_RIGHT:
                return width - dto.watermark_width, height - dto.watermark_height
            case WatermarkPosition.CENTER:
                return (width - dto.watermark_width) // 2, (height - dto.watermark_height) // 2


async def set_params_for_document(dto: BaseModel, target_model: MODEL = None) -> dict | None:
    """
    POST: If target_model is not transferred, create dict (return dict).
    PUT: Receives target_model and sets attributes (return None).
    """
    if target_model is None:
        kwrgs = dict()
        for field, value in dto.dict().items():
            if value:
                if "date" in field:
                    kwrgs.update({field: datetime.strptime(value, settings.DATE_FORMAT)})
                elif field == "photo":
                    kwrgs.update({field: await VisitorPhoto.get_or_none(id=value)})
                else:
                    kwrgs.update({field: value})
        return kwrgs

    for field, value in dto.dict().items():
        if value:
            if "date" in field:
                setattr(target_model, field, datetime.strptime(value, settings.DATE_FORMAT))
            elif field == "photo":
                setattr(target_model, field, await VisitorPhoto.get_or_none(id=value))
            else:
                setattr(target_model, field, value)
