import base64
import itertools
from datetime import datetime
from io import BytesIO

import qrcode
from barcode import Code128
from barcode.writer import SVGWriter
from tortoise.transactions import atomic

from web_foundation.environment.services.service import Service
from web_foundation.utils.helpers import validate_datetime

from application.exceptions import InconsistencyError
from asbp_app import settings
from asbp_app.api.dto.access import SystemUser, EntityId
from asbp_app.enviroment.infrastructure.database.models import Pass


class PassService(Service):
    target_model = Pass

    # for descendants
    # async def generate_rfid(self) -> int:
    #         rfid = self.rfid.__next__()
    #         while await Pass.exists(rfid=rfid):
    #             rfid += 1
    #         self.rfid = itertools.count(rfid + 1)
    #         return rfid


    @atomic()
    async def create_qr_code(self, entity: EntityId) -> str:
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

    @atomic()
    async def create_barcode(self, entity: EntityId) -> str:
        """Creating BAR code from Pass.rfid"""
        pass_id = await Pass.get_or_none(id=entity).only("rfid")
        if pass_id.rfid is None:
            raise InconsistencyError(message="To create barcode RFID couldn't be NULL.")
        Code128(pass_id.rfid, writer=SVGWriter()).write(buffered := BytesIO())
        bar_code = str(base64.b64encode(buffered.getvalue()))
        buffered.close()
        return bar_code
