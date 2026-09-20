"""Dữ liệu registry giả lập: danh mục, đội, đầu mối, link đã duyệt, form, quy trình, người dùng.

Mọi giá trị là GIẢ ĐỊNH để mô phỏng (tên miền vsf-demo.example không tồn tại). Không có số điện thoại hay tên cá nhân.
"""
from __future__ import annotations

DEFAULT_AS_OF = "2026-09-20"
DEV_PASSWORD = "ChangeMe!123"  # chỉ dùng cho môi trường dev/test cục bộ

CATEGORIES = [
    {"slug": "quy-dinh-chung", "name": "Quy định chung", "description": "Nội quy lao động, giờ làm việc, trang phục, làm việc từ xa, quy định văn phòng"},
    {"slug": "nghi-phep", "name": "Nghỉ phép và nghỉ lễ", "description": "Số ngày phép năm, cách đăng ký nghỉ phép, chuyển phép, nghỉ lễ"},
    {"slug": "thu-viec", "name": "Thử việc", "description": "Thời gian thử việc, lương thử việc, đánh giá thử việc, quyền lợi khi thử việc"},
    {"slug": "phuc-loi-bao-hiem", "name": "Phúc lợi và bảo hiểm", "description": "Bảo hiểm, phụ cấp, thưởng, khám sức khỏe, ưu đãi hệ sinh thái"},
    {"slug": "bao-mat-thong-tin", "name": "An toàn và bảo mật thông tin", "description": "Mật khẩu, xác thực nhiều yếu tố, phân loại dữ liệu, báo cáo sự cố bảo mật"},
    {"slug": "van-hoa", "name": "Văn hóa và giá trị", "description": "Giá trị cốt lõi, văn hóa công ty, quy tắc ứng xử"},
    {"slug": "onboarding-ngay-dau", "name": "Onboarding và ngày đầu", "description": "Ngày đầu đi làm, giấy tờ, lịch tuần đầu, thẻ từ, thẻ xe, hỏi đáp onboarding"},
    {"slug": "thiet-bi-tai-khoan", "name": "Thiết bị, tài khoản và phần mềm", "description": "Cấp phát máy, hệ điều hành, tài khoản, VPN, cài phần mềm, cấp quyền"},
    {"slug": "phan-cong-mentor-cho-ngoi", "name": "Mentor, buddy và chỗ ngồi", "description": "Cách biết mentor và buddy, nhận và đổi chỗ ngồi"},
    {"slug": "ho-tro-it", "name": "Hỗ trợ IT và đầu mối", "description": "Danh bạ đầu mối theo đội, kênh hỗ trợ, ứng dụng nội bộ"},
    {"slug": "gioi-thieu-cong-ty", "name": "Giới thiệu công ty", "description": "Sứ mệnh, cơ cấu, văn phòng, quy mô"},
    {"slug": "phap-luat-lao-dong", "name": "Pháp luật lao động", "description": "Bộ luật Lao động, bảo hiểm xã hội, công đoàn, bảo vệ dữ liệu cá nhân"},
]

TEAMS = [
    {"code": "HR_ONBOARDING", "name": "HR Onboarding", "ticket_prefix": "HR", "description": "Tiếp nhận nhân sự mới, phân công Mentor/Buddy, chỗ ngồi ban đầu"},
    {"code": "IT", "name": "IT Helpdesk", "ticket_prefix": "IT", "description": "Thiết bị, tài khoản, VPN, phần mềm, cấp quyền"},
    {"code": "VINSOC", "name": "VinSOC", "ticket_prefix": "SOC", "description": "Kiểm tra bảo mật, quét và duyệt link phần mềm, sự cố bảo mật"},
    {"code": "FACILITIES", "name": "Facilities", "ticket_prefix": "FAC", "description": "Chỗ ngồi, thẻ từ, thẻ xe"},
]

USERS = [
    {"email": "admin@vsf-demo.example", "display_name": "Admin Demo", "role": "ADMIN", "teams": []},
    {"email": "hr1@vsf-demo.example", "display_name": "HR Demo 1", "role": "HR", "teams": ["HR_ONBOARDING"]},
    {"email": "hr2@vsf-demo.example", "display_name": "HR Demo 2", "role": "HR", "teams": ["HR_ONBOARDING"]},
    {"email": "it.staff@vsf-demo.example", "display_name": "IT Staff Demo", "role": "USER", "teams": ["IT"]},
    {"email": "soc.staff@vsf-demo.example", "display_name": "SOC Staff Demo", "role": "USER", "teams": ["VINSOC"]},
    {"email": "fac.staff@vsf-demo.example", "display_name": "Facilities Staff Demo", "role": "USER", "teams": ["FACILITIES"]},
    {"email": "newhire1@vsf-demo.example", "display_name": "Nhân sự mới 1", "role": "USER", "teams": []},
    {"email": "newhire2@vsf-demo.example", "display_name": "Nhân sự mới 2", "role": "USER", "teams": []},
    {"email": "newhire3@vsf-demo.example", "display_name": "Nhân sự mới 3", "role": "USER", "teams": []},
]

CONTACT_CHANNELS = [
    {"key": "hr-email", "team": "HR_ONBOARDING", "kind": "EMAIL", "label": "Email HR Onboarding", "value": "hr-onboarding@vsf-demo.example", "status": "ACTIVE"},
    {"key": "hr-portal", "team": "HR_ONBOARDING", "kind": "PORTAL", "label": "HR Portal", "value": "https://hr.vsf-demo.example", "status": "ACTIVE"},
    {"key": "it-email", "team": "IT", "kind": "EMAIL", "label": "Email IT Helpdesk", "value": "it-helpdesk@vsf-demo.example", "status": "ACTIVE"},
    {"key": "it-portal", "team": "IT", "kind": "PORTAL", "label": "Cổng IT", "value": "https://it.vsf-demo.example/requests", "status": "ACTIVE"},
    {"key": "soc-oncall", "team": "VINSOC", "kind": "EMAIL", "label": "Trực SOC (sự cố bảo mật)", "value": "soc-oncall@vsf-demo.example", "status": "ACTIVE"},
    {"key": "fac-email", "team": "FACILITIES", "kind": "EMAIL", "label": "Email Facilities", "value": "facilities@vsf-demo.example", "status": "ACTIVE"},
    {"key": "fac-portal", "team": "FACILITIES", "kind": "PORTAL", "label": "Cổng Facilities", "value": "https://facilities.vsf-demo.example/requests", "status": "ACTIVE"},
    {"key": "reception-desk", "team": "FACILITIES", "kind": "IN_PERSON", "label": "Quầy tiếp nhận",
     "value": "Hà Nội: tầng 1 tòa TechnoPark. TP. Hồ Chí Minh: tầng trệt Vincom Center Đồng Khởi", "status": "ACTIVE"},
    {"key": "old-fax", "team": "HR_ONBOARDING", "kind": "EMAIL", "label": "Email HR cũ (đã ngừng)", "value": "hr-old@vsf-demo.example", "status": "ARCHIVED"},
]

LINKS = [
    {"key": "L-IT-PORTAL", "url": "https://it.vsf-demo.example/requests", "label": "Cổng yêu cầu IT", "status": "APPROVED",
     "requires_security_review": False, "security_review": None, "verified_by": "hr1@vsf-demo.example", "verified_at": "2026-06-20", "effective_from": "2026-07-01", "effective_to": None},
    {"key": "L-SOFTWARE-CATALOG", "url": "https://it.vsf-demo.example/software-catalog", "label": "Danh mục phần mềm được duyệt", "status": "APPROVED",
     "requires_security_review": True, "security_review": {"reviewer_team": "VINSOC", "result": "PASSED", "reference": "SOC-2026-0142", "reviewed_at": "2026-06-25"},
     "verified_by": "it.staff@vsf-demo.example", "verified_at": "2026-06-26", "effective_from": "2026-07-01", "effective_to": None},
    {"key": "L-VPN-CLIENT", "url": "https://it.vsf-demo.example/software-catalog/vpn", "label": "Tải ứng dụng VPN", "status": "APPROVED",
     "requires_security_review": True, "security_review": {"reviewer_team": "VINSOC", "result": "PASSED", "reference": "SOC-2026-0143", "reviewed_at": "2026-06-25"},
     "verified_by": "it.staff@vsf-demo.example", "verified_at": "2026-06-26", "effective_from": "2026-07-01", "effective_to": None},
    {"key": "L-HR-LEAVE", "url": "https://hr.vsf-demo.example/leave", "label": "Đăng ký nghỉ phép trên HR Portal", "status": "APPROVED",
     "requires_security_review": False, "security_review": None, "verified_by": "hr1@vsf-demo.example", "verified_at": "2026-06-20", "effective_from": "2026-07-01", "effective_to": None},
    {"key": "L-FAC-PORTAL", "url": "https://facilities.vsf-demo.example/requests", "label": "Cổng yêu cầu Facilities", "status": "APPROVED",
     "requires_security_review": False, "security_review": None, "verified_by": "hr1@vsf-demo.example", "verified_at": "2026-06-20", "effective_from": "2026-07-01", "effective_to": None},
    # Không được hiển thị cho người dùng:
    {"key": "L-UBUNTU-INSTALLER-DRAFT", "url": "https://tools.vsf-demo.example/ubuntu-installer", "label": "Bộ cài Ubuntu (chờ VinSOC duyệt)", "status": "PENDING_REVIEW",
     "requires_security_review": True, "security_review": {"reviewer_team": "VINSOC", "result": "PENDING", "reference": None, "reviewed_at": None},
     "verified_by": None, "verified_at": None, "effective_from": None, "effective_to": None},
    {"key": "L-VPN-LEGACY", "url": "https://old.vsf-demo.example/vpn", "label": "VPN cũ (đã thu hồi)", "status": "REVOKED",
     "requires_security_review": True, "security_review": {"reviewer_team": "VINSOC", "result": "FAILED", "reference": "SOC-2025-0999", "reviewed_at": "2025-11-01"},
     "verified_by": "it.staff@vsf-demo.example", "verified_at": "2025-10-01", "effective_from": "2025-01-01", "effective_to": "2025-11-01"},
    {"key": "L-OLD-PORTAL", "url": "https://old.vsf-demo.example/portal", "label": "Cổng cũ (hết hiệu lực)", "status": "APPROVED",
     "requires_security_review": False, "security_review": None, "verified_by": "hr1@vsf-demo.example", "verified_at": "2024-12-01", "effective_from": "2025-01-01", "effective_to": "2025-12-31"},
]


def _f(key, label, type_, required=True, options=None, help_=None):
    d = {"key": key, "label": label, "type": type_, "required": required}
    if options:
        d["options"] = options
    if help_:
        d["help"] = help_
    return d


FORMS = [
    {"code": "IT-DEV-01", "version_no": 1, "name": "Yêu cầu cấu hình thiết bị", "team": "IT", "status": "ACTIVE", "effective_from": "2026-07-01", "effective_to": None,
     "fields": [_f("employee_id", "Mã nhân viên", "text"), _f("department", "Đơn vị", "text"), _f("device_id", "Mã thiết bị", "text"),
                _f("os_request", "Hệ điều hành cần cấu hình", "select", options=["Ubuntu 22.04 LTS", "Windows 11"]),
                _f("note", "Mô tả nhu cầu", "textarea", required=False)]},
    {"code": "IT-SW-01", "version_no": 1, "name": "Yêu cầu cài phần mềm", "team": "IT", "status": "ACTIVE", "effective_from": "2026-07-01", "effective_to": None,
     "fields": [_f("employee_id", "Mã nhân viên", "text"), _f("software_name", "Tên phần mềm", "text"),
                _f("business_reason", "Lý do công việc", "textarea"), _f("proposed_link", "Liên kết đề xuất (nếu có)", "text", required=False)]},
    {"code": "IT-ACC-01", "version_no": 1, "name": "Yêu cầu cấp quyền hệ thống", "team": "IT", "status": "ACTIVE", "effective_from": "2026-07-01", "effective_to": None,
     "fields": [_f("employee_id", "Mã nhân viên", "text"), _f("system_name", "Hệ thống cần truy cập", "text"),
                _f("access_level", "Mức quyền", "select", options=["Đọc", "Ghi", "Quản trị"]),
                _f("business_reason", "Lý do", "textarea"), _f("manager_email", "Email quản lý phê duyệt", "text")]},
    {"code": "FAC-01", "version_no": 1, "name": "Yêu cầu đổi chỗ ngồi", "team": "FACILITIES", "status": "ACTIVE", "effective_from": "2026-07-01", "effective_to": None,
     "fields": [_f("employee_id", "Mã nhân viên", "text"), _f("current_location", "Vị trí hiện tại", "text", required=False),
                _f("requested_location", "Vị trí mong muốn", "text"), _f("reason", "Lý do", "textarea")]},
    {"code": "FAC-02", "version_no": 1, "name": "Đăng ký thẻ xe", "team": "FACILITIES", "status": "ACTIVE", "effective_from": "2026-07-01", "effective_to": None,
     "fields": [_f("employee_id", "Mã nhân viên", "text"), _f("vehicle_type", "Loại xe", "select", options=["Xe máy", "Ô tô"]),
                _f("plate_number", "Biển số xe", "text")]},
]


def _s(order, text, links=(), contacts=()):
    return {"order": order, "text": text, "link_keys": list(links), "contact_keys": list(contacts)}


_COMMON = {"version_no": 1, "status": "ACTIVE", "effective_from": "2026-07-01", "effective_to": None}

PROCEDURES = [
    {**_COMMON, "code": "PR-DEVICE-CONFIG", "title": "Cấu hình hoặc cài lại thiết bị", "category": "thiet-bi-tai-khoan",
     "trigger_text": "Nhân sự cần cấu hình lại máy, cài hoặc cài lại hệ điều hành (ví dụ Ubuntu) cho máy công ty.",
     "conditions": [{"slot": "department", "op": "present"}], "responsible_team": "IT", "ticket_required": True, "form_code": "IT-DEV-01",
     "steps": [_s(1, "Không tự cài hoặc cài lại hệ điều hành; IT cấu hình máy theo đơn vị."),
               _s(2, "Mở form yêu cầu cấu hình thiết bị IT-DEV-01 tại cổng IT.", links=["L-IT-PORTAL"]),
               _s(3, "Điền mã nhân viên, đơn vị, mã thiết bị, hệ điều hành cần cấu hình và mô tả nhu cầu."),
               _s(4, "Gửi yêu cầu vào hàng đợi IT; IT xử lý trong 2 ngày làm việc.", contacts=["it-email"]),
               _s(5, "Chỉ dùng tệp hoặc liên kết cài đặt trong Danh mục phần mềm được duyệt.", links=["L-SOFTWARE-CATALOG"])],
     "next_step": "Chờ IT hướng dẫn qua kênh đã xác minh; không dùng liên kết cài đặt nhận qua chat hoặc email.",
     "source_docs": ["P06", "P07"], "sample_questions": ["Vậy cài Ubuntu sao?", "Tôi muốn cài lại hệ điều hành cho máy", "Xin cấu hình lại máy"],
     "aliases": ["cài OS", "cài máy", "cấu hình máy"]},
    {**_COMMON, "code": "PR-SOFTWARE-REQUEST", "title": "Yêu cầu cài phần mềm và kiểm tra VinSOC", "category": "thiet-bi-tai-khoan",
     "trigger_text": "Nhân sự cần cài phần mềm ngoài danh mục chuẩn.", "conditions": [], "responsible_team": "IT", "ticket_required": True, "form_code": "IT-SW-01",
     "steps": [_s(1, "Tạo yêu cầu bằng form IT-SW-01 trên cổng IT, nêu tên phần mềm và lý do công việc.", links=["L-IT-PORTAL"]),
               _s(2, "IT chuyển yêu cầu tới VinSOC; VinSOC quét liên kết và tệp cài đặt trong 3 ngày làm việc.", contacts=["it-email"]),
               _s(3, "Sau khi được duyệt, chỉ tải phần mềm từ Danh mục phần mềm được duyệt.", links=["L-SOFTWARE-CATALOG"]),
               _s(4, "Không mở liên kết cài đặt nhận qua chat hoặc email.")],
     "next_step": "Chờ VinSOC công bố kết quả trong Danh mục phần mềm được duyệt.", "source_docs": ["P07"],
     "sample_questions": ["Tôi cần cài phần mềm Docker", "Xin cài phần mềm mới", "Cho tôi link tải phần mềm"], "aliases": ["cài app", "cài phần mềm"]},
    {**_COMMON, "code": "PR-FIND-SEAT", "title": "Tìm chỗ ngồi ban đầu", "category": "phan-cong-mentor-cho-ngoi",
     "trigger_text": "Nhân sự mới hỏi chỗ ngồi hoặc vị trí ngồi của mình.", "conditions": [], "responsible_team": "HR_ONBOARDING", "ticket_required": False, "form_code": None,
     "steps": [_s(1, "Kiểm tra Thư tiếp nhận do đầu mối bộ phận gửi trước ngày đầu tiên; vị trí ngồi được ghi trong thư."),
               _s(2, "Nếu chưa có thông tin, liên hệ đầu mối HR Onboarding.", contacts=["hr-email"]),
               _s(3, "Khi đến nơi, báo họ tên và bộ phận tại Quầy tiếp nhận để được dẫn tới vị trí.", contacts=["reception-desk"])],
     "next_step": "Nếu vẫn chưa có thông tin sau khi liên hệ HR Onboarding, hỏi lại đầu mối bộ phận.", "source_docs": ["P04", "P01"],
     "sample_questions": ["Mai tôi ngồi chỗ nào?", "Chỗ ngồi của tôi ở đâu", "Tôi ngồi bàn nào"], "aliases": ["vị trí ngồi", "bàn làm việc"]},
    {**_COMMON, "code": "PR-SEAT-CHANGE", "title": "Đổi chỗ ngồi", "category": "phan-cong-mentor-cho-ngoi",
     "trigger_text": "Nhân sự muốn đổi chỗ ngồi sau khi đã có chỗ.", "conditions": [], "responsible_team": "FACILITIES", "ticket_required": True, "form_code": "FAC-01",
     "steps": [_s(1, "Mở form yêu cầu đổi chỗ ngồi FAC-01 trên cổng Facilities.", links=["L-FAC-PORTAL"]),
               _s(2, "Yêu cầu vào hàng đợi Facilities và được xử lý trong 3 ngày làm việc.", contacts=["fac-email"])],
     "next_step": "Chờ Facilities xác nhận vị trí mới.", "source_docs": ["P04"],
     "sample_questions": ["Muốn đổi chỗ ngồi thì sao?", "Xin chuyển chỗ ngồi"], "aliases": ["chuyển chỗ"]},
    {**_COMMON, "code": "PR-FIND-MENTOR", "title": "Biết Mentor và Buddy của mình", "category": "phan-cong-mentor-cho-ngoi",
     "trigger_text": "Nhân sự mới hỏi Mentor hoặc Buddy của mình là ai.", "conditions": [], "responsible_team": "HR_ONBOARDING", "ticket_required": False, "form_code": None,
     "steps": [_s(1, "Kiểm tra Thư giới thiệu đội; danh sách Mentor và Buddy được gửi chậm nhất 2 ngày làm việc trước ngày đầu tiên."),
               _s(2, "Nếu chưa nhận được thư, liên hệ đầu mối HR Onboarding để được xác nhận.", contacts=["hr-email"]),
               _s(3, "Không nhờ quản lý trực tiếp làm Mentor hoặc Buddy; quản lý chỉ xác nhận thông tin phân công.")],
     "next_step": "Nếu chưa được phân công, HR Onboarding sẽ xác nhận với đầu mối bộ phận.", "source_docs": ["P03"],
     "sample_questions": ["Mentor của tôi là ai?", "Buddy của tôi là ai", "Ai là người hướng dẫn tôi"], "aliases": ["người hướng dẫn", "cố vấn"]},
    {**_COMMON, "code": "PR-ACCOUNT-ACTIVATION", "title": "Kích hoạt tài khoản lần đầu", "category": "thiet-bi-tai-khoan",
     "trigger_text": "Nhân sự mới kích hoạt tài khoản email và MFA.", "conditions": [], "responsible_team": "IT", "ticket_required": False, "form_code": None,
     "steps": [_s(1, "Dùng điện thoại truy cập email đăng ký để nhận thư kích hoạt."),
               _s(2, "Đặt mật khẩu mới theo Chính sách mật khẩu và bật xác thực nhiều yếu tố."),
               _s(3, "Mật khẩu tạm phải được đổi trong vòng 24 giờ."),
               _s(4, "Nếu không kích hoạt được, liên hệ IT Helpdesk.", contacts=["it-email"])],
     "next_step": "Liên hệ IT Helpdesk nếu quá 24 giờ chưa đổi được mật khẩu tạm.", "source_docs": ["P08", "D08b"],
     "sample_questions": ["Kích hoạt tài khoản email lần đầu như thế nào?", "Mật khẩu tạm đổi ra sao"], "aliases": ["kích hoạt email"]},
    {**_COMMON, "code": "PR-VPN-SETUP", "title": "Cài và kết nối VPN", "category": "thiet-bi-tai-khoan",
     "trigger_text": "Nhân sự cần cài VPN hoặc gặp lỗi VPN.", "conditions": [], "responsible_team": "IT", "ticket_required": False, "form_code": None,
     "steps": [_s(1, "Tải ứng dụng VPN từ Cổng phần mềm đã duyệt.", links=["L-VPN-CLIENT"]),
               _s(2, "Nhập máy chủ VPN do IT cung cấp và đăng nhập bằng tài khoản công ty."),
               _s(3, "Nếu không kết nối được, liên hệ IT Helpdesk.", contacts=["it-email"])],
     "next_step": "Liên hệ IT Helpdesk nếu vẫn lỗi sau khi thử lại.", "source_docs": ["P08"],
     "sample_questions": ["Cài VPN thế nào?", "Không kết nối được VPN liên hệ ai"], "aliases": ["vpn"]},
    {**_COMMON, "code": "PR-SYSTEM-ACCESS", "title": "Xin cấp quyền hệ thống", "category": "thiet-bi-tai-khoan",
     "trigger_text": "Nhân sự cần quyền truy cập một hệ thống nội bộ.", "conditions": [], "responsible_team": "IT", "ticket_required": True, "form_code": "IT-ACC-01",
     "steps": [_s(1, "Tạo yêu cầu bằng form IT-ACC-01 trên cổng IT, nêu hệ thống và lý do.", links=["L-IT-PORTAL"]),
               _s(2, "Quản lý trực tiếp phê duyệt yêu cầu trên cổng."),
               _s(3, "IT cấp quyền trong 2 ngày làm việc sau khi được phê duyệt.", contacts=["it-email"])],
     "next_step": "Chờ quản lý phê duyệt; không xin quyền qua chat hoặc email.", "source_docs": ["P09"],
     "sample_questions": ["Xin quyền vào hệ thống thì làm sao?", "Cấp quyền truy cập hệ thống"], "aliases": ["xin quyền"]},
    {**_COMMON, "code": "PR-SECURITY-INCIDENT", "title": "Báo cáo sự cố bảo mật", "category": "bao-mat-thong-tin",
     "trigger_text": "Nhân sự nghi ngờ mã độc, mất thiết bị hoặc tài khoản bị chiếm quyền.", "conditions": [], "responsible_team": "VINSOC", "ticket_required": False, "form_code": None,
     "steps": [_s(1, "Không tự xử lý và không xóa dấu vết trên thiết bị."),
               _s(2, "Ngắt kết nối mạng của thiết bị (rút cáp mạng hoặc tắt Wi-Fi)."),
               _s(3, "Báo cho Trực SOC trong vòng 1 giờ kể từ khi phát hiện.", contacts=["soc-oncall"]),
               _s(4, "Ghi nhận mã sự cố do Trực SOC cung cấp và làm theo hướng dẫn.")],
     "next_step": "Làm theo hướng dẫn của Trực SOC.", "source_docs": ["D10"],
     "sample_questions": ["Máy tôi nghi nhiễm mã độc thì làm gì?", "Mất laptop công ty phải báo ai"], "aliases": ["mã độc", "virus"]},
    {**_COMMON, "code": "PR-PARKING-CARD", "title": "Đăng ký thẻ xe", "category": "onboarding-ngay-dau",
     "trigger_text": "Nhân sự cần gửi xe tại tòa nhà.", "conditions": [], "responsible_team": "FACILITIES", "ticket_required": True, "form_code": "FAC-02",
     "steps": [_s(1, "Đăng ký thẻ xe bằng form FAC-02 trên cổng Facilities.", links=["L-FAC-PORTAL"]),
               _s(2, "Yêu cầu vào hàng đợi Facilities và xử lý trong 3 ngày làm việc.", contacts=["fac-email"])],
     "next_step": "Nhận thẻ xe theo hướng dẫn của Facilities.", "source_docs": ["P10"],
     "sample_questions": ["Đăng ký thẻ xe làm sao?", "Tôi muốn gửi xe máy"], "aliases": ["gửi xe", "thẻ xe"]},
    {**_COMMON, "code": "PR-LEAVE-REGISTRATION", "title": "Đăng ký nghỉ phép", "category": "nghi-phep",
     "trigger_text": "Nhân viên chính thức cần đăng ký nghỉ phép.", "conditions": [], "responsible_team": "HR_ONBOARDING", "ticket_required": False, "form_code": None,
     "steps": [_s(1, "Đăng ký nghỉ phép trên HR Portal trước ít nhất 2 ngày làm việc.", links=["L-HR-LEAVE"]),
               _s(2, "Nghỉ từ 5 ngày liên tục trở lên cần trưởng phòng phê duyệt.")],
     "next_step": "Chờ quản lý phê duyệt trên HR Portal.", "source_docs": ["D03b"],
     "sample_questions": ["Đăng ký nghỉ phép ở đâu?", "Xin nghỉ phép thế nào"], "aliases": ["xin nghỉ"]},
]

# ---------------------------------------------------------------------------- fixture sai để kiểm tra bộ quy tắc
_BAD_BASE = {**_COMMON, "title": "Fixture lỗi", "category": "thiet-bi-tai-khoan", "trigger_text": "fixture", "conditions": [],
             "responsible_team": "IT", "ticket_required": False, "form_code": None, "next_step": None, "source_docs": [],
             "sample_questions": [], "aliases": [], "steps": [_s(1, "bước 1")]}

INVALID_PROCEDURES = [
    {"case": "ticket_required_without_form", "expected_errors": ["INV18"], "procedures": [{**_BAD_BASE, "code": "BAD-1", "ticket_required": True, "form_code": None}]},
    {"case": "form_code_not_active", "expected_errors": ["REF_FORM"], "procedures": [{**_BAD_BASE, "code": "BAD-2", "ticket_required": True, "form_code": "IT-NOPE-99"}]},
    {"case": "step_links_pending_link", "expected_errors": ["INV15"], "procedures": [{**_BAD_BASE, "code": "BAD-3", "steps": [_s(1, "x", links=["L-UBUNTU-INSTALLER-DRAFT"])]}]},
    {"case": "step_links_revoked_link", "expected_errors": ["INV15"], "procedures": [{**_BAD_BASE, "code": "BAD-4", "steps": [_s(1, "x", links=["L-VPN-LEGACY"])]}]},
    {"case": "step_links_expired_link", "expected_errors": ["INV15"], "procedures": [{**_BAD_BASE, "code": "BAD-5", "steps": [_s(1, "x", links=["L-OLD-PORTAL"])]}]},
    {"case": "unknown_link_key", "expected_errors": ["REF_LINK"], "procedures": [{**_BAD_BASE, "code": "BAD-6", "steps": [_s(1, "x", links=["L-KHONG-TON-TAI"])]}]},
    {"case": "archived_contact", "expected_errors": ["REF_CONTACT"], "procedures": [{**_BAD_BASE, "code": "BAD-7", "steps": [_s(1, "x", contacts=["old-fax"])]}]},
    {"case": "overlapping_active_versions", "expected_errors": ["INV17"],
     "procedures": [{**_BAD_BASE, "code": "BAD-8", "version_no": 1, "effective_from": "2026-01-01", "effective_to": None},
                    {**_BAD_BASE, "code": "BAD-8", "version_no": 2, "effective_from": "2026-06-01", "effective_to": None}]},
]

INVALID_LINKS = [
    {"case": "link_http_not_https", "expected_errors": ["INV15_URL"],
     "link": {"key": "BAD-L1", "url": "http://it.vsf-demo.example/x", "label": "x", "status": "APPROVED", "requires_security_review": False, "security_review": None,
              "verified_by": "hr1@vsf-demo.example", "verified_at": "2026-06-01", "effective_from": None, "effective_to": None}},
    {"case": "approved_without_verifier", "expected_errors": ["INV15_VERIFIED"],
     "link": {"key": "BAD-L2", "url": "https://it.vsf-demo.example/x", "label": "x", "status": "APPROVED", "requires_security_review": False, "security_review": None,
              "verified_by": None, "verified_at": None, "effective_from": None, "effective_to": None}},
    {"case": "approved_security_not_passed", "expected_errors": ["INV15_SECURITY"],
     "link": {"key": "BAD-L3", "url": "https://it.vsf-demo.example/x", "label": "x", "status": "APPROVED", "requires_security_review": True,
              "security_review": {"reviewer_team": "VINSOC", "result": "PENDING", "reference": None, "reviewed_at": None},
              "verified_by": "hr1@vsf-demo.example", "verified_at": "2026-06-01", "effective_from": None, "effective_to": None}},
]
