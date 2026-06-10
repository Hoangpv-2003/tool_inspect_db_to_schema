from pydantic import BaseModel
from typing import Optional

class TableSchema(BaseModel):
    stt: int
    ten_csdl: str
    ten_bang: str
    mo_ta: str = ""
    so_truong: int
    so_ban_ghi: int
    nhom_du_lieu: str = ""
    co_du_lieu_ca_nhan: str = ""
    tan_suat_cap_nhat: str = ""
    khoa_dinh_danh: str
    nguoi_quan_ly: str = ""
    lineage: str = ""
    ngay_cap_nhat: Optional[str] = None
    thoi_han_luu_tru: str = ""
    giay_phep: str = ""
    ghi_chu: str = ""
