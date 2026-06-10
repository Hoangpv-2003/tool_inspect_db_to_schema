import pytest
from pydantic import ValidationError
from db_schema_crawler.models.table_schema import TableSchema
from db_schema_crawler.models.field_schema import FieldSchema

def test_table_schema_defaults():
    # Only supply required fields
    table = TableSchema(
        stt=1,
        ten_csdl="CSDL_GiaDat",
        ten_bang="users",
        so_truong=5,
        so_ban_ghi=100,
        khoa_dinh_danh="id"
    )
    assert table.stt == 1
    assert table.ten_csdl == "CSDL_GiaDat"
    assert table.ten_bang == "users"
    assert table.mo_ta == ""
    assert table.so_truong == 5
    assert table.so_ban_ghi == 100
    assert table.nhom_du_lieu == ""
    assert table.co_du_lieu_ca_nhan == ""
    assert table.tan_suat_cap_nhat == ""
    assert table.khoa_dinh_danh == "id"
    assert table.nguoi_quan_ly == ""
    assert table.lineage == ""
    assert table.ngay_cap_nhat is None
    assert table.thoi_han_luu_tru == ""
    assert table.giay_phep == ""
    assert table.ghi_chu == ""

def test_field_schema_required_fields():
    # Missing ten_truong_ky_thuat
    with pytest.raises(ValidationError):
        FieldSchema(
            stt=1,
            ten_csdl="CSDL_GiaDat",
            ten_bang="users",
            kieu_du_lieu="varchar",
            do_dai_dinh_dang="50 ký tự",
            bat_buoc="Có",
            khoa="PK"
        )

def test_table_schema_serialization():
    table = TableSchema(
        stt=1,
        ten_csdl="CSDL_GiaDat",
        ten_bang="users",
        so_truong=5,
        so_ban_ghi=100,
        khoa_dinh_danh="id"
    )
    dumped = table.model_dump()
    assert len(dumped) == 16
    assert dumped["stt"] == 1
    assert dumped["ten_csdl"] == "CSDL_GiaDat"
    assert dumped["ten_bang"] == "users"
