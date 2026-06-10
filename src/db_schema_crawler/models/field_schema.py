from pydantic import BaseModel

class FieldSchema(BaseModel):
    stt: int
    ten_csdl: str
    ten_bang: str
    ten_truong_nghiep_vu: str = ""
    ten_truong_ky_thuat: str
    kieu_du_lieu: str
    do_dai_dinh_dang: str
    bat_buoc: str
    khoa: str
    danh_sach_gia_tri: str = ""
    dinh_nghia_nghiep_vu: str = ""
    du_lieu_ca_nhan: str = ""
    anh_xa: str = ""
    ghi_chu: str = ""
