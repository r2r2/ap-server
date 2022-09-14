from typing import Type

import base64

from io import BytesIO
from PIL import ImageDraw, Image, UnidentifiedImageError
from web_foundation.errors.app.application import InconsistencyError

from asbp_app.api.dto.access import VisitorPhotoDto
from asbp_app.enviroment.infrastructure.database.models import WaterMark, WatermarkPosition, SystemSettingsTypes
from asbp_app.utils.system import get_system_settings


class WaterMarkUtil:
    target_model = WaterMark

    @staticmethod
    async def apply_watermark(dto: VisitorPhotoDto.CreationDto | VisitorPhotoDto.UpdateDto,
                              w_type: str = "image") -> None:
        """Add watermark to the images"""
        watermark = await WaterMarkUtil._get_watermark(w_type, dto)
        image_format: str = await get_system_settings(SystemSettingsTypes.WATERMARK_FORMAT)
        if w_type == "text":
            font_size: int = await get_system_settings(SystemSettingsTypes.WATERMARK_FONT_SIZE)
            font_type: str = await get_system_settings(SystemSettingsTypes.WATERMARK_FONT_TYPE)
            font_rgb_color = await get_system_settings(
                SystemSettingsTypes.WATERMARK_FONT_RGB_COLOR)
            color = font_rgb_color.split(",")
            font_rgb_color = tuple(map(int, color))

        for field, value in dto.dict().items():
            if isinstance(value, list):
                for image in value:
                    buffered = BytesIO()
                    b64image = base64.b64decode(image)
                    try:
                        with Image.open(BytesIO(b64image)) as base_image:
                            width, height = base_image.size  # In pixels
                            coordinates = await WaterMarkUtil._get_coordinates(width, height, dto)

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
                        transparency: int = await get_system_settings(SystemSettingsTypes.WATERMARK_TRANSPARENCY)
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

