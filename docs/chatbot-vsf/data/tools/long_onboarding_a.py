"""Bản dài (giả lập) cho P01, P01b, P02, P03, P04, P05, P10 - nhóm onboarding ngày đầu.

Mọi dữ kiện là GIẢ ĐỊNH để kiểm thử chatbot. Không có tên cá nhân, số điện thoại, số ghế hay dữ liệu phân công cá nhân.
"""
from __future__ import annotations

from blocks import H1, H2, P, B, N, T, PB  # noqa: F401

_NOTE = "Tài liệu giả lập để kiểm thử, không phải quy trình VSF đã xác nhận"
_HR = "Phòng Nhân sự (giả định), nhóm HR Onboarding"
_FAC = "Ban Hành chính - Cơ sở vật chất (giả định)"


# =====================================================================================================================
# P01 và P01b: cùng cấu trúc và văn phong, chỉ khác giờ có mặt và mốc thời gian trong ngày
# =====================================================================================================================
def _day_one(code, ver, period, scope_note, arr, a_end, i_end, buddy, gap_note, history):
    return [
        H1("Thông tin kiểm soát tài liệu"),
        T(["Hạng mục", "Nội dung"], [
            ["Mã tài liệu", code],
            ["Tên tài liệu", "Hướng dẫn ngày đầu đi làm"],
            ["Phiên bản", ver],
            ["Đơn vị sở hữu", _HR],
            ["Người phê duyệt", "Trưởng phòng Nhân sự"],
            ["Đối tượng áp dụng", "Nhân sự mới tại văn phòng Hà Nội và TP. Hồ Chí Minh"],
            ["Thời gian hiệu lực", period],
            ["Phân loại", "Nội bộ"],
            ["Ghi chú", _NOTE],
        ], widths=[4, 9]),
        P(scope_note),

        H1("Mục đích, phạm vi và đối tượng"),
        H2("Mục đích"),
        P("Tài liệu này mô tả chi tiết những việc nhân sự mới cần chuẩn bị và sẽ trải qua trong ngày đầu tiên đi làm: giờ và địa điểm có mặt, "
          "giấy tờ cần mang, lịch trong ngày, cách nhận thẻ từ, gặp Buddy, nhận thiết bị và biết chỗ ngồi. Mục tiêu là để mọi nhân sự mới, "
          "dù vào làm ở văn phòng nào, đều có trải nghiệm tiếp nhận giống nhau, không bị thiếu giấy tờ hoặc lúng túng vì không biết tìm ai."),
        H2("Phạm vi"),
        P("Tài liệu áp dụng cho mọi nhân sự mới, gồm nhân viên chính thức, nhân viên thử việc và thực tập sinh, bắt đầu làm việc tại văn phòng Hà Nội hoặc văn phòng TP. Hồ Chí Minh. "
          "Tài liệu chỉ nói về ngày đầu tiên và những việc bắt buộc hoàn tất ngay sau ngày đó. Lịch cho cả tuần đầu được mô tả riêng trong tài liệu Lịch tuần đầu tiên của nhân sự mới."),
        P("Tài liệu không nêu thông tin cá nhân của bất kỳ nhân sự nào. Vị trí ngồi, người được phân công làm Mentor hoặc Buddy, mã nhân viên và các thông tin tương tự được gửi riêng cho từng người qua thư, "
          "chatbot hỗ trợ onboarding không có dữ liệu này."),
        H2("Tài liệu liên quan"),
        B("Lịch tuần đầu tiên của nhân sự mới: lịch từ Thứ Hai đến Thứ Sáu của tuần đầu.",
          "Chương trình Mentor và Buddy: vai trò, thời gian đồng hành và cách biết người được phân công.",
          "Quy trình nhận chỗ ngồi và đổi chỗ ngồi: cách biết chỗ ngồi và đổi chỗ sau đó.",
          "Hướng dẫn nhận thẻ từ và đăng ký thẻ xe: thẻ từ, thẻ xe và cách xử lý khi thẻ gặp sự cố.",
          "Danh bạ đầu mối theo đội: kênh liên hệ HR Onboarding, IT Helpdesk, Facilities và Quầy tiếp nhận.",
          "Hướng dẫn cấp phát và cấu hình thiết bị: thiết bị được cấu hình và bàn giao như thế nào.",
          "Hướng dẫn kích hoạt tài khoản và cài VPN: kích hoạt tài khoản email và bật xác thực nhiều yếu tố."),

        H1("Định nghĩa và thuật ngữ"),
        T(["Thuật ngữ", "Ý nghĩa trong tài liệu này"], [
            ["Ngày đầu tiên", "Ngày làm việc đầu tiên ghi trong thư nhận việc của nhân sự mới."],
            ["Quầy tiếp nhận", "Điểm đón nhân sự mới tại từng văn phòng, nơi làm thủ tục và phát thẻ từ."],
            ["Thư nhận việc", "Thư xác nhận đề nghị làm việc, có kèm danh sách hồ sơ cần bổ sung."],
            ["Thư tiếp nhận", "Thư do quản lý hoặc đầu mối bộ phận gửi trước ngày đầu tiên, có ghi vị trí ngồi."],
            ["Thư giới thiệu đội", "Thư giới thiệu đội và danh sách phân công Mentor, Buddy."],
            ["Thẻ từ", "Thẻ ra vào tòa nhà, được nhận tại Quầy tiếp nhận trong ngày đầu tiên."],
            ["Email đăng ký", "Địa chỉ email nhân sự đã cung cấp khi nhận việc, dùng để nhận thư kích hoạt tài khoản."],
            ["Bàn IT", "Điểm bàn giao thiết bị của IT tại khu vực tiếp nhận."],
            ["Buddy", "Đồng nghiệp cùng bộ phận hỗ trợ văn hóa và hòa nhập cho nhân sự mới."],
            ["Đầu mối bộ phận", "Người được bộ phận chỉ định làm việc với HR Onboarding về nhân sự mới."],
        ], widths=[3.2, 9.8]),

        H1("Vai trò và trách nhiệm"),
        T(["Vai trò", "Trách nhiệm trong ngày đầu", "Thời điểm"], [
            ["HR Onboarding", "Đón, kiểm tra giấy tờ, phát thẻ từ, giải đáp thủ tục.", "Từ giờ có mặt đến hết buổi giới thiệu"],
            ["Quản lý trực tiếp", "Gửi Thư tiếp nhận có vị trí ngồi, xác nhận thông tin phân công.", "Trước ngày đầu tiên"],
            ["Đầu mối bộ phận", "Chuẩn bị khu vực làm việc, báo HR Onboarding khi có thay đổi.", "Trước và trong ngày đầu tiên"],
            ["Buddy", "Đón nhân sự tại khu vực làm việc của đội, giới thiệu đồng nghiệp.", "Theo lịch gặp trong ngày"],
            ["IT Helpdesk", "Bàn giao thiết bị, hướng dẫn kích hoạt tài khoản.", "Buổi chiều"],
            ["Facilities", "Quản lý thẻ từ, chỗ ngồi và thẻ xe.", "Trong và sau ngày đầu tiên"],
            ["Nhân sự mới", "Có mặt đúng giờ, mang đủ giấy tờ, báo sớm khi có vấn đề.", "Cả ngày"],
        ], widths=[2.8, 6.4, 3.8]),

        H1("Quy trình chi tiết"),
        H2("Chuẩn bị trước ngày đầu tiên"),
        P("Phần lớn các vướng mắc của ngày đầu tiên đến từ việc chuẩn bị chưa đủ. Nhân sự mới nên hoàn tất các việc sau trước ngày đầu tiên."),
        N("Đọc lại Thư nhận việc và ghi lại danh sách hồ sơ còn thiếu. Hồ sơ còn thiếu theo thư nhận việc phải được mang theo vào ngày đầu tiên nếu chưa nộp trước.",
          "Kiểm tra hộp thư email đăng ký để chắc chắn đã nhận được Thư tiếp nhận và Thư giới thiệu đội. Nếu chưa nhận thư nào, liên hệ HR Onboarding qua hr-onboarding@vsf-demo.example để được xác nhận.",
          "Xác định văn phòng làm việc là Hà Nội hay TP. Hồ Chí Minh để đến đúng Quầy tiếp nhận.",
          "Chuẩn bị điện thoại có thể truy cập email đăng ký, đã đăng nhập sẵn ứng dụng thư hoặc biết mật khẩu email, để kích hoạt tài khoản công ty trong ngày.",
          "Sắp xếp phương tiện đi lại sao cho có mặt đúng giờ, có tính đến giờ cao điểm. Nếu cần gửi xe, đọc trước Hướng dẫn nhận thẻ từ và đăng ký thẻ xe.",
          "Chuẩn bị trang phục lịch sự theo Nội quy trang phục hiện hành."),
        T(["Mốc thời gian", "Việc phải hoàn tất", "Người thực hiện"], [
            ["Chậm nhất 2 ngày làm việc trước ngày đầu tiên", "Gửi Thư giới thiệu đội có danh sách Mentor và Buddy", "HR Onboarding"],
            ["Trước ngày đầu tiên", "Gửi Thư tiếp nhận có vị trí ngồi", "Quản lý hoặc đầu mối bộ phận"],
            ["Trước ngày đầu tiên", "Chuẩn bị thiết bị nếu đã có thông tin thiết bị", "IT Helpdesk"],
            ["Ngày liền trước ngày đầu tiên", "Rà soát lại giấy tờ và lộ trình di chuyển", "Nhân sự mới"],
        ], widths=[4.2, 5.8, 3]),

        H2("Giờ và địa điểm có mặt"),
        P("Nhân sự mới có mặt lúc " + arr + " tại quầy tiếp nhận của văn phòng nơi mình làm việc. Địa điểm tiếp nhận của hai văn phòng là giả định dựa trên thông tin công khai."),
        T(["Văn phòng", "Địa điểm tiếp nhận", "Giờ có mặt"], [
            ["Hà Nội", "Quầy tiếp nhận tầng 1, tòa TechnoPark", arr],
            ["TP. Hồ Chí Minh", "Quầy lễ tân tầng trệt, Vincom Center Đồng Khởi", arr],
        ], widths=[3, 8, 2]),
        P("Nhân sự nên đến đúng giờ có mặt. Đến quá sớm có thể chưa có người đón, đến muộn sẽ làm lùi các mốc tiếp theo trong ngày. Nếu không chắc mình thuộc văn phòng nào, "
          "kiểm tra Thư nhận việc hoặc hỏi HR Onboarding trước ngày đầu tiên."),

        H2("Giấy tờ cần mang"),
        B("Căn cước công dân bản gốc. Bản gốc được đối chiếu trực tiếp tại Quầy tiếp nhận, ảnh chụp hoặc bản sao không thay thế được.",
          "Hồ sơ còn thiếu theo thư nhận việc. Chỉ mang những giấy tờ mà thư nhận việc liệt kê là chưa nộp.",
          "Điện thoại có thể truy cập email đăng ký để kích hoạt tài khoản. Máy phải còn pin và có kết nối mạng."),
        P("Nhân sự không cần mang máy tính cá nhân. Thiết bị làm việc do IT bàn giao trong ngày. Nếu có giấy tờ nào chưa chuẩn bị kịp, xem mục Trường hợp đặc biệt và ngoại lệ bên dưới."),

        H2("Lịch trong ngày"),
        T(["Thời gian", "Nội dung", "Địa điểm"], [
            [arr + " - " + a_end, "Làm thủ tục tiếp nhận và nhận thẻ từ", "Quầy tiếp nhận của văn phòng"],
            [a_end + " - " + i_end, "Giới thiệu công ty và an toàn thông tin", "Phòng đào tạo"],
            [buddy, "Gặp Buddy được phân công", "Khu vực làm việc của đội"],
            ["14:00", "Nhận và ký xác nhận thiết bị", "Bàn IT tại khu vực tiếp nhận"],
        ], widths=[2.5, 6, 4.5]),
        P("Các mục dưới đây mô tả từng mốc trong lịch. Thời gian ở giữa các mốc dùng để di chuyển, nghỉ ngắn, nghỉ trưa theo Nội quy lao động và làm quen khu vực làm việc."),

        H2("Mốc 1: tiếp nhận và nhận thẻ từ"),
        N("Đến Quầy tiếp nhận của văn phòng mình và báo họ tên, bộ phận cho nhân viên tiếp nhận.",
          "Xuất trình Căn cước công dân bản gốc để đối chiếu với hồ sơ.",
          "Nộp hồ sơ còn thiếu (nếu có) và nhận xác nhận đã nộp.",
          "Nhận thẻ từ, kiểm tra thẻ có hiển thị đúng thông tin rồi ký nhận.",
          "Được hướng dẫn cách sử dụng thẻ khi vào tòa nhà và các khu vực được phép.",
          "Nhận thông tin về vị trí phòng đào tạo cho mốc tiếp theo."),
        P("Kết quả của mốc này là nhân sự có thẻ từ trong tay, hồ sơ được ghi nhận đầy đủ hoặc có danh sách hồ sơ cần bổ sung kèm hạn nộp, và biết đường tới Phòng đào tạo. "
          "Nếu thẻ chưa sẵn sàng, xem hướng dẫn trong Hướng dẫn nhận thẻ từ và đăng ký thẻ xe."),

        H2("Mốc 2: giới thiệu công ty và an toàn thông tin"),
        P("Buổi giới thiệu diễn ra tại Phòng đào tạo và giới thiệu ngắn về công ty, cách các khối phối hợp với nhau, nơi tìm hỗ trợ và những nguyên tắc an toàn thông tin cơ bản mà mọi nhân sự phải nắm ngay từ ngày đầu. "
          "Nhân sự nên ghi chú lại những đầu mối được nhắc tới và đặt câu hỏi ngay trong buổi nếu chưa rõ. Nội dung đào tạo an toàn thông tin sâu hơn do VinSOC thực hiện trong tuần đầu, "
          "xem Lịch tuần đầu tiên của nhân sự mới."),
        P(gap_note),

        H2("Mốc 3: gặp Buddy"),
        P("Buddy là đồng nghiệp cùng bộ phận, đã được phân công và thông báo trong Thư giới thiệu đội. Buổi gặp diễn ra tại khu vực làm việc của đội. Buddy giới thiệu các đồng nghiệp, "
          "chỉ nhà vệ sinh, khu vực pha nước, phòng họp và cách gọi hỗ trợ. Buddy không thay thế quản lý trực tiếp và không phải người quyết định vị trí ngồi. "
          "Vai trò chi tiết của Buddy được nêu trong Chương trình Mentor và Buddy."),
        B("Nhân sự nên hỏi Buddy về quy ước làm việc hằng ngày của đội, nơi ăn trưa và cách trao đổi trong đội.",
          "Nếu chưa gặp được Buddy tại giờ hẹn, chờ tại khu vực làm việc của đội và báo cho quản lý trực tiếp hoặc HR Onboarding.",
          "Không cần chờ Buddy để bắt đầu đọc tài liệu giới thiệu mà quản lý gửi."),

        H2("Mốc 4: nhận thiết bị lúc 14:00"),
        N("Đến Bàn IT tại khu vực tiếp nhận vào lúc 14:00.",
          "Kiểm tra thiết bị được bàn giao, gồm máy và phụ kiện đi kèm, theo phiếu bàn giao.",
          "Ký xác nhận thiết bị. Nhân sự chịu trách nhiệm bảo quản thiết bị từ thời điểm ký.",
          "Dùng điện thoại truy cập email đăng ký để nhận thư kích hoạt, đặt mật khẩu mới và bật xác thực nhiều yếu tố ngay tại Bàn IT nếu cần hỗ trợ.",
          "Ghi nhận cách liên hệ IT Helpdesk qua it-helpdesk@vsf-demo.example hoặc cổng IT khi gặp lỗi."),
        P("IT cấu hình máy trước ngày đầu tiên nếu đã có thông tin thiết bị. Nhân sự không tự cài hoặc cài lại hệ điều hành. Mật khẩu tạm phải được đổi trong vòng 24 giờ, "
          "chi tiết nằm trong Hướng dẫn kích hoạt tài khoản và cài VPN."),

        H2("Chỗ ngồi"),
        P("Vị trí ngồi được quản lý thông báo trong Thư tiếp nhận gửi trước ngày đầu tiên. Quầy tiếp nhận không quyết định vị trí ngồi. Khi đến nơi, nhân sự báo họ tên và bộ phận "
          "tại Quầy tiếp nhận để được dẫn tới vị trí đã ghi trong thư. Nếu Thư tiếp nhận chưa có thông tin về chỗ ngồi, liên hệ đầu mối HR Onboarding. Muốn đổi chỗ ngồi sau đó, "
          "dùng form FAC-01 trên cổng Facilities theo Quy trình nhận chỗ ngồi và đổi chỗ ngồi."),

        H2("Kết thúc ngày đầu và việc cần làm sau đó"),
        B("Rà soát lại danh sách hồ sơ còn thiếu và nộp đúng hạn đã ghi tại Quầy tiếp nhận.",
          "Nếu cần gửi xe, đăng ký thẻ xe bằng form FAC-02 trên cổng Facilities.",
          "Đọc Lịch tuần đầu tiên của nhân sự mới để biết các buổi đào tạo sắp tới.",
          "Trao đổi với quản lý trực tiếp về kỳ vọng công việc của tuần đầu.",
          "Ghi lại các vướng mắc của ngày đầu để phản hồi với Buddy vào cuối tuần."),

        H2("Cam kết thời gian"),
        T(["Hạng mục", "Thời hạn", "Đơn vị thực hiện"], [
            ["Gửi Thư giới thiệu đội", "Chậm nhất 2 ngày làm việc trước ngày đầu tiên", "HR Onboarding"],
            ["Gửi Thư tiếp nhận", "Trước ngày đầu tiên", "Quản lý hoặc đầu mối bộ phận"],
            ["Nhận thẻ từ", "Trong ngày đầu tiên, tại Quầy tiếp nhận", "HR Onboarding và Facilities"],
            ["Bàn giao thiết bị", "14:00 ngày đầu tiên", "IT Helpdesk"],
            ["Xử lý form đổi chỗ ngồi hoặc thẻ xe", "3 ngày làm việc", "Facilities"],
        ], widths=[4.5, 5.5, 3]),

        H1("Trường hợp đặc biệt và ngoại lệ"),
        T(["Tình huống", "Cách xử lý"], [
            ["Đến muộn so với giờ có mặt", "Báo ngay HR Onboarding và quản lý trực tiếp, đến Quầy tiếp nhận làm thủ tục rồi tham gia nốt các mốc còn lại; các buổi đã lỡ sẽ được sắp xếp lại."],
            ["Thiếu hồ sơ theo thư nhận việc", "Vẫn làm thủ tục tiếp nhận, ghi rõ hồ sơ còn thiếu và hạn nộp bổ sung với HR Onboarding."],
            ["Quên Căn cước công dân bản gốc", "Báo ngay cho Quầy tiếp nhận, không thể hoàn tất thủ tục cho tới khi xuất trình bản gốc; HR Onboarding sẽ hướng dẫn phương án."],
            ["Không truy cập được email đăng ký", "Báo IT Helpdesk và HR Onboarding để kiểm tra địa chỉ email đã đăng ký, không dùng email khác để nhận thư kích hoạt."],
            ["Ốm hoặc không thể đến", "Báo cho quản lý trực tiếp và HR Onboarding trước giờ có mặt để dời ngày tiếp nhận."],
            ["Chưa nhận Thư tiếp nhận hoặc Thư giới thiệu đội", "Liên hệ HR Onboarding qua hr-onboarding@vsf-demo.example để được xác nhận lại."],
            ["Làm việc tại địa điểm khác văn phòng ghi trong thư", "Xác nhận với HR Onboarding địa điểm tiếp nhận trước ngày đầu tiên."],
        ], widths=[4.2, 8.8]),

        H2("Lỗi thường gặp và cách xử lý"),
        T(["Tình huống", "Nguyên nhân", "Cách xử lý"], [
            ["Đến nhầm tòa nhà", "Nhầm giữa hai văn phòng", "Kiểm tra lại văn phòng trong thư nhận việc và báo HR Onboarding"],
            ["Thẻ từ không mở được cửa", "Thẻ chưa kích hoạt hoặc đưa sai đầu đọc", "Quay lại Quầy tiếp nhận để kiểm tra"],
            ["Không thấy thư kích hoạt", "Thư nằm trong thư rác hoặc sai địa chỉ", "Kiểm tra thư rác, sau đó báo IT Helpdesk"],
            ["Không tìm thấy Buddy", "Buddy đang bận hoặc nhầm khu vực", "Báo quản lý trực tiếp hoặc HR Onboarding"],
            ["Không biết chỗ ngồi", "Chưa đọc Thư tiếp nhận hoặc thư chưa được gửi", "Báo họ tên và bộ phận tại Quầy tiếp nhận, liên hệ HR Onboarding"],
            ["Thiết bị báo lỗi khi nhận", "Máy chưa cấu hình xong", "Ghi lại lỗi trên phiếu bàn giao và gửi yêu cầu cho IT Helpdesk"],
        ], widths=[3.4, 4.2, 5.4]),

        H1("Checklist và mẫu thông báo"),
        H2("Checklist cho nhân sự mới"),
        B("Đã biết văn phòng và địa điểm Quầy tiếp nhận của mình.",
          "Đã đọc Thư tiếp nhận và Thư giới thiệu đội.",
          "Đã có Căn cước công dân bản gốc.",
          "Đã có hồ sơ còn thiếu theo thư nhận việc.",
          "Điện thoại đã sẵn sàng truy cập email đăng ký.",
          "Đã ghi lại giờ có mặt là " + arr + " và giờ nhận thiết bị là 14:00.",
          "Đã biết cách liên hệ HR Onboarding khi có vướng mắc."),
        H2("Checklist cho quản lý trực tiếp và đầu mối bộ phận"),
        B("Gửi Thư tiếp nhận có vị trí ngồi trước ngày đầu tiên.",
          "Xác nhận Buddy đã biết lịch gặp nhân sự mới.",
          "Chuẩn bị khu vực làm việc và thông báo cho Facilities nếu cần điều chỉnh.",
          "Sắp xếp một buổi trao đổi ngắn về kỳ vọng tuần đầu.",
          "Không tự nhận làm Mentor hoặc Buddy cho nhân sự mới của mình."),
        H2("Mẫu email báo đến muộn"),
        P("Kính gửi HR Onboarding, tôi là nhân sự mới bắt đầu làm việc hôm nay tại [văn phòng]. Do [lý do ngắn gọn], tôi sẽ đến Quầy tiếp nhận muộn hơn giờ có mặt. "
          "Tôi đã mang Căn cước công dân bản gốc và hồ sơ theo thư nhận việc. Xin hướng dẫn giúp tôi cách tham gia các mốc còn lại. Trân trọng."),
        H2("Mẫu email hỏi chỗ ngồi"),
        P("Kính gửi HR Onboarding, tôi sắp bắt đầu làm việc và chưa nhận được Thư tiếp nhận có thông tin vị trí ngồi. Nhờ HR Onboarding xác nhận giúp với đầu mối bộ phận. Trân trọng."),

        H1("Câu hỏi thường gặp"),
        P("Hỏi: Ngày đầu tiên tôi phải đến lúc mấy giờ? Đáp: Nhân sự mới có mặt lúc " + arr + " tại quầy tiếp nhận của văn phòng nơi mình làm việc."),
        P("Hỏi: Tôi làm việc ở Hà Nội thì đến đâu? Đáp: Đến Quầy tiếp nhận tầng 1, tòa TechnoPark."),
        P("Hỏi: Tôi làm việc ở TP. Hồ Chí Minh thì đến đâu? Đáp: Đến Quầy lễ tân tầng trệt, Vincom Center Đồng Khởi."),
        P("Hỏi: Tôi cần mang giấy tờ gì? Đáp: Căn cước công dân bản gốc, hồ sơ còn thiếu theo thư nhận việc và điện thoại có thể truy cập email đăng ký."),
        P("Hỏi: Tôi nhận thẻ từ ở đâu? Đáp: Nhận tại Quầy tiếp nhận trong ngày đầu tiên, cùng với thủ tục tiếp nhận."),
        P("Hỏi: Khi nào tôi gặp Buddy? Đáp: Buổi gặp Buddy bắt đầu lúc " + buddy + " tại khu vực làm việc của đội."),
        P("Hỏi: Tôi nhận thiết bị lúc nào? Đáp: Lúc 14:00 tại Bàn IT ở khu vực tiếp nhận, và ký xác nhận thiết bị."),
        P("Hỏi: Quầy tiếp nhận có xếp chỗ ngồi cho tôi không? Đáp: Không. Quầy tiếp nhận không quyết định vị trí ngồi; vị trí được ghi trong Thư tiếp nhận."),
        P("Hỏi: Tôi chưa nhận được Thư tiếp nhận thì sao? Đáp: Liên hệ đầu mối HR Onboarding qua hr-onboarding@vsf-demo.example để được xác nhận."),
        P("Hỏi: Chatbot có cho tôi biết chỗ ngồi hoặc Buddy của tôi không? Đáp: Không. Chatbot không có dữ liệu phân công cá nhân, thông tin này nằm trong thư gửi riêng cho từng người."),

        H1("Lịch sử sửa đổi"),
        T(["Phiên bản", "Ngày", "Nội dung thay đổi"], history, widths=[2.4, 3, 7.6]),
    ]


_P01_HISTORY = [
    ["3.0", "2026-03-01", "Ban hành bản đầy đủ đầu tiên về ngày đầu đi làm."],
    ["3.1", "2026-06-01", "Bổ sung phần Trường hợp đặc biệt và ngoại lệ, cập nhật địa điểm Quầy tiếp nhận."],
    ["3.2", "2026-09-01", "Bổ sung checklist cho quản lý trực tiếp và mẫu email; làm rõ vai trò của Quầy tiếp nhận về chỗ ngồi."],
]

_P01B_HISTORY = [
    ["3.0", "2026-03-01", "Ban hành bản đầy đủ đầu tiên về ngày đầu đi làm."],
    ["3.1", "2026-06-01", "Bổ sung phần Trường hợp đặc biệt và ngoại lệ, cập nhật địa điểm Quầy tiếp nhận."],
    ["3.2", "2026-09-01", "Bổ sung checklist cho quản lý trực tiếp và mẫu email; làm rõ vai trò của Quầy tiếp nhận về chỗ ngồi."],
    ["3.3", "2026-10-01", "Thay đổi giờ có mặt của nhân sự mới; các mốc trong ngày được điều chỉnh tương ứng. Các nội dung khác giữ nguyên."],
]

_P01 = _day_one(
    "SYN-P01", "3.2", "Từ 01/09/2026 đến hết 30/09/2026",
    "Phiên bản này áp dụng cho nhân sự bắt đầu làm việc trong khoảng thời gian hiệu lực nêu trên. Nhân sự bắt đầu làm việc từ ngày 01/10/2026 áp dụng phiên bản kế tiếp của tài liệu này.",
    "8:15", "9:00", "10:00", "10:00",
    "Buổi giới thiệu kết thúc đúng lúc bắt đầu buổi gặp Buddy, nên nhân sự nên đi thẳng từ Phòng đào tạo tới khu vực làm việc của đội.",
    _P01_HISTORY)

_P01B = _day_one(
    "SYN-P01b", "3.3", "Từ 01/10/2026, thay thế phiên bản 3.2 kể từ ngày có hiệu lực",
    "Phiên bản này thay thế phiên bản 3.2 kể từ ngày 01/10/2026 và áp dụng cho nhân sự bắt đầu làm việc từ ngày đó. Nhân sự bắt đầu làm việc trước ngày này thực hiện theo phiên bản 3.2.",
    "8:30", "9:15", "10:15", "10:30",
    "Giữa lúc kết thúc buổi giới thiệu và buổi gặp Buddy có một khoảng nghỉ ngắn, nhân sự dùng khoảng này để uống nước và di chuyển tới khu vực làm việc của đội.",
    _P01B_HISTORY)


# =====================================================================================================================
# P02 Lịch tuần đầu tiên của nhân sự mới
# =====================================================================================================================
_P02 = [
    H1("Thông tin kiểm soát tài liệu"),
    T(["Hạng mục", "Nội dung"], [
        ["Mã tài liệu", "SYN-P02"],
        ["Tên tài liệu", "Lịch tuần đầu tiên của nhân sự mới"],
        ["Phiên bản", "1.0"],
        ["Đơn vị sở hữu", _HR],
        ["Người phê duyệt", "Trưởng phòng Nhân sự"],
        ["Đối tượng áp dụng", "Nhân sự mới, quản lý trực tiếp, Buddy, Mentor"],
        ["Phân loại", "Nội bộ"],
        ["Ghi chú", _NOTE],
    ], widths=[4, 9]),

    H1("Mục đích, phạm vi và đối tượng"),
    P("Tài liệu này giới thiệu lịch năm ngày làm việc của tuần đầu tiên, từ Thứ Hai đến Thứ Sáu, để nhân sự mới biết trước mình sẽ làm gì, gặp ai và cần chuẩn bị gì ở mỗi ngày. "
      "Lịch được thiết kế theo hướng đi từ thủ tục hành chính, sang an toàn thông tin, sang định hướng công việc với Mentor, sang công cụ làm việc và kết thúc bằng buổi nhìn lại tuần đầu cùng Buddy."),
    P("Tài liệu áp dụng cho mọi nhân sự mới của công ty. Giờ có mặt và các mốc chi tiết của ngày đầu tiên nằm trong tài liệu Hướng dẫn ngày đầu đi làm hiện hành, "
      "vì vậy tài liệu này không nhắc lại giờ có mặt. Cách phân công Mentor và Buddy nằm trong Chương trình Mentor và Buddy. Danh sách đầu mối liên hệ nằm trong Danh bạ đầu mối theo đội."),
    H2("Tài liệu liên quan"),
    B("Hướng dẫn ngày đầu đi làm: giờ có mặt, giấy tờ và lịch trong ngày đầu tiên.",
      "Chương trình Mentor và Buddy: vai trò và thời gian đồng hành.",
      "Hướng dẫn cấp phát và cấu hình thiết bị: bàn giao thiết bị cho nhân sự mới.",
      "Hướng dẫn kích hoạt tài khoản và cài VPN: kích hoạt tài khoản và xác thực nhiều yếu tố.",
      "Danh bạ đầu mối theo đội: nơi liên hệ khi lịch có thay đổi."),

    H1("Định nghĩa và thuật ngữ"),
    T(["Thuật ngữ", "Ý nghĩa"], [
        ["Tuần đầu tiên", "Năm ngày làm việc tính từ Thứ Hai của tuần nhân sự mới bắt đầu làm việc."],
        ["Đội phụ trách", "Đội chuyên môn hoặc đơn vị đào tạo chịu trách nhiệm tổ chức một buổi trong tuần."],
        ["Lời mời lịch", "Thư mời họp do đơn vị tổ chức gửi, ghi thời gian và địa điểm cụ thể của buổi."],
        ["Mục tiêu tháng đầu", "Danh sách kết quả mong đợi trong tháng đầu, thống nhất giữa nhân sự mới và Mentor."],
        ["Buổi tổng kết tuần", "Buổi trao đổi cuối tuần giữa nhân sự mới và Buddy để nhìn lại trải nghiệm."],
        ["Phiếu phản hồi tuần đầu", "Biểu mẫu ngắn để nhân sự mới ghi nhận ý kiến về tuần đầu tiên."],
    ], widths=[3.4, 9.6]),

    H1("Vai trò và trách nhiệm"),
    T(["Vai trò", "Trách nhiệm trong tuần đầu"], [
        ["HR Onboarding", "Phụ trách tiếp nhận ngày Thứ Hai, theo dõi tiến độ tuần và tiếp nhận phản hồi."],
        ["IT Helpdesk", "Bàn giao thiết bị, hỗ trợ kích hoạt tài khoản, giải đáp lỗi thiết bị."],
        ["VinSOC", "Tổ chức buổi đào tạo an toàn thông tin vào Thứ Ba."],
        ["Mentor", "Gặp nhân sự mới vào Thứ Tư, thống nhất mục tiêu tháng đầu."],
        ["Đội phụ trách công cụ", "Tổ chức buổi đào tạo công cụ làm việc vào Thứ Năm."],
        ["Buddy", "Đồng hành cả tuần và dẫn buổi tổng kết vào Thứ Sáu."],
        ["Quản lý trực tiếp", "Xác nhận lịch, giải phóng thời gian để nhân sự mới tham gia các buổi."],
        ["Nhân sự mới", "Tham gia đầy đủ, chuẩn bị theo checklist, điền phiếu phản hồi cuối tuần."],
    ], widths=[3.4, 9.6]),

    H1("Quy trình chi tiết"),
    H2("Lịch tuần đầu"),
    T(["Ngày", "Hoạt động", "Người phụ trách"], [
        ["Thứ Hai", "Tiếp nhận, nhận thẻ từ và thiết bị", "HR Onboarding và IT"],
        ["Thứ Ba", "Đào tạo an toàn thông tin (1 giờ)", "VinSOC"],
        ["Thứ Tư", "Gặp Mentor, thống nhất mục tiêu tháng đầu", "Mentor"],
        ["Thứ Năm", "Đào tạo công cụ làm việc", "Đội phụ trách"],
        ["Thứ Sáu", "Tổng kết tuần và phản hồi với Buddy", "Buddy"],
    ], widths=[2, 8, 4]),
    P("Thời gian cụ thể của các buổi từ Thứ Ba đến Thứ Sáu được thông báo qua lời mời lịch của đơn vị tổ chức. Nhân sự mới nên chấp nhận lời mời và ghi lại vào lịch cá nhân ngay khi nhận được."),

    H2("Thứ Hai: tiếp nhận, nhận thẻ từ và thiết bị"),
    P("Đây là ngày đầu tiên, các mốc chi tiết được mô tả trong Hướng dẫn ngày đầu đi làm. Nhân sự làm thủ tục tại Quầy tiếp nhận, nhận thẻ từ, tham gia buổi giới thiệu công ty, gặp Buddy và nhận thiết bị từ IT vào buổi chiều."),
    B("Đầu ra: có thẻ từ, có thiết bị đã ký nhận, tài khoản công ty được kích hoạt và đã bật xác thực nhiều yếu tố.",
      "Chuẩn bị: giấy tờ theo Hướng dẫn ngày đầu đi làm và điện thoại truy cập được email đăng ký.",
      "Lưu ý: nếu ngày đầu tiên không rơi vào Thứ Hai, HR Onboarding thông báo lịch dời tương ứng cho nhân sự mới trong Thư tiếp nhận."),

    H2("Thứ Ba: đào tạo an toàn thông tin"),
    P("VinSOC tổ chức buổi đào tạo an toàn thông tin kéo dài 1 giờ dành cho nhân sự mới. Buổi này giúp nhân sự hiểu các nguyên tắc bảo vệ tài khoản, nhận diện thư giả mạo, cách sử dụng thiết bị công ty và cách báo cáo sự cố. "
      "Nhân sự nên mang theo thiết bị đã nhận và sẵn sàng đăng nhập để thực hành các bước bảo mật."),
    B("Đầu ra: nhân sự nắm được kênh báo cáo sự cố và các nguyên tắc cơ bản về mật khẩu, xác thực nhiều yếu tố, phân loại dữ liệu.",
      "Chuẩn bị: thiết bị đã kích hoạt, tài khoản đã đăng nhập được.",
      "Nếu vắng buổi này, thông báo cho HR Onboarding để được sắp xếp buổi bù, không tự tìm tài liệu ngoài."),

    H2("Thứ Tư: gặp Mentor và thống nhất mục tiêu tháng đầu"),
    P("Mentor là nhân viên cấp Senior trở lên, không phải quản lý trực tiếp, đồng hành với nhân sự mới trong 6 tháng đầu. Buổi gặp đầu tiên nhằm làm quen, tìm hiểu nền tảng chuyên môn của nhân sự mới "
      "và thống nhất mục tiêu tháng đầu. Mục tiêu nên cụ thể, có thể quan sát được và phù hợp với vai trò được giao."),
    B("Đầu ra: bản ghi ngắn về mục tiêu tháng đầu và cách thức trao đổi tiếp theo với Mentor.",
      "Chuẩn bị: đọc lại mô tả công việc, liệt kê các chủ đề muốn được định hướng, các câu hỏi về kỹ thuật và nghề nghiệp.",
      "Nếu chưa biết ai là Mentor của mình, kiểm tra Thư giới thiệu đội hoặc liên hệ HR Onboarding."),

    H2("Thứ Năm: đào tạo công cụ làm việc"),
    P("Đội phụ trách hướng dẫn các công cụ nhân sự sẽ dùng hằng ngày như hệ thống quản lý công việc, kho tài liệu và kênh trao đổi nội bộ. Nội dung cụ thể có thể khác nhau giữa các đội. "
      "Khi cần thêm quyền truy cập, gửi yêu cầu theo quy trình của IT chứ không xin trực tiếp qua chat."),
    B("Đầu ra: nhân sự đăng nhập và thao tác được trên các công cụ chính của đội.",
      "Chuẩn bị: danh sách công cụ đội sử dụng, hỏi Buddy nếu chưa rõ.",
      "Chỉ cài phần mềm từ Danh mục phần mềm được duyệt, không tự tải ứng dụng ngoài danh mục."),

    H2("Thứ Sáu: tổng kết tuần và phản hồi với Buddy"),
    P("Buddy là đồng nghiệp cùng bộ phận, có thâm niên từ 6 tháng, hỗ trợ văn hóa và hòa nhập trong 3 tháng đầu. Buổi tổng kết tuần là dịp để nhân sự mới nói về những điều đã ổn, "
      "những điều còn vướng và những việc cần hỗ trợ trong tuần kế tiếp. Buddy ghi nhận và chuyển các vấn đề cần xử lý cho đầu mối phù hợp."),
    B("Đầu ra: phiếu phản hồi tuần đầu được điền và danh sách việc cần hỗ trợ cho tuần sau.",
      "Chuẩn bị: ghi chú lại các vướng mắc theo từng ngày trong tuần.",
      "Nếu không thoải mái nói với Buddy, nhân sự có thể gửi phản hồi trực tiếp cho HR Onboarding."),

    H2("Kỳ vọng đối với nhân sự mới trong tuần đầu"),
    B("Tham gia đầy đủ các buổi đã có lời mời lịch và báo trước nếu có xung đột.",
      "Chủ động đặt câu hỏi, ghi chép và phản hồi sớm khi có điều chưa rõ.",
      "Không cần tạo ra sản phẩm công việc chính thức trong tuần đầu; ưu tiên là hiểu bối cảnh, công cụ và cách phối hợp trong đội.",
      "Giữ liên lạc thường xuyên với quản lý trực tiếp và Buddy."),

    H2("Checklist chuẩn bị"),
    B("Đã đọc Hướng dẫn ngày đầu đi làm hiện hành và biết giờ có mặt.",
      "Đã đọc Thư tiếp nhận và Thư giới thiệu đội.",
      "Đã ghi lại lịch Thứ Hai đến Thứ Sáu vào lịch cá nhân.",
      "Đã chuẩn bị danh sách câu hỏi cho Mentor và Buddy.",
      "Đã biết kênh liên hệ HR Onboarding và IT Helpdesk."),
    H2("Cần mang theo và sử dụng trong tuần"),
    B("Căn cước công dân bản gốc và hồ sơ còn thiếu vào ngày đầu tiên.",
      "Điện thoại truy cập được email đăng ký.",
      "Thẻ từ và thiết bị đã nhận, mang theo mỗi ngày.",
      "Sổ tay hoặc ứng dụng ghi chú để ghi lại nội dung các buổi đào tạo."),

    H2("Mẫu phiếu phản hồi tuần đầu"),
    T(["Mục", "Nội dung cần điền"], [
        ["Điều làm tốt", "Ba việc trong tuần khiến bạn thấy thuận lợi."],
        ["Điều còn vướng", "Các khó khăn về thủ tục, thiết bị, tài khoản hoặc công cụ."],
        ["Buổi hữu ích nhất", "Chọn một buổi trong tuần và nêu lý do."],
        ["Đề xuất cải tiến", "Ý kiến để tuần đầu của nhân sự sau tốt hơn."],
        ["Hỗ trợ cần thiết", "Việc cần Buddy, Mentor, quản lý hoặc HR Onboarding hỗ trợ."],
    ], widths=[3.4, 9.6]),

    H1("Trường hợp đặc biệt và ngoại lệ"),
    T(["Tình huống", "Nguyên nhân", "Cách xử lý"], [
        ["Tuần có ngày nghỉ lễ", "Lịch nghỉ lễ của công ty", "HR Onboarding thông báo lịch điều chỉnh trong Thư tiếp nhận"],
        ["Vắng một buổi do ốm", "Lý do sức khỏe", "Báo quản lý và HR Onboarding, buổi vắng được sắp xếp bù"],
        ["Chưa gặp được Mentor Thứ Tư", "Mentor bận hoặc chưa nhận lịch", "Báo HR Onboarding để xác nhận lại lịch"],
        ["Chưa có lời mời lịch buổi Thứ Năm", "Đội chưa gửi", "Hỏi Buddy hoặc quản lý trực tiếp"],
        ["Chưa đăng nhập được công cụ", "Chưa có quyền", "Gửi yêu cầu cấp quyền theo quy trình của IT"],
    ], widths=[3.8, 3.6, 5.6]),

    H1("Câu hỏi thường gặp"),
    P("Hỏi: Thứ Ba tôi học gì và trong bao lâu? Đáp: Buổi đào tạo an toàn thông tin do VinSOC tổ chức, kéo dài 1 giờ."),
    P("Hỏi: Ai phụ trách ngày Thứ Hai? Đáp: HR Onboarding và IT, gồm tiếp nhận, nhận thẻ từ và thiết bị."),
    P("Hỏi: Thứ Tư tôi làm gì? Đáp: Gặp Mentor và thống nhất mục tiêu tháng đầu."),
    P("Hỏi: Thứ Năm ai tổ chức đào tạo công cụ? Đáp: Đội phụ trách; nội dung có thể khác nhau giữa các đội."),
    P("Hỏi: Thứ Sáu tôi làm gì? Đáp: Tổng kết tuần và phản hồi với Buddy, kèm điền phiếu phản hồi tuần đầu."),
    P("Hỏi: Giờ bắt đầu từng buổi ở đâu? Đáp: Được ghi trong lời mời lịch của đơn vị tổ chức."),
    P("Hỏi: Tôi có phải tạo sản phẩm công việc trong tuần đầu không? Đáp: Không bắt buộc, trọng tâm là hiểu bối cảnh, công cụ và cách phối hợp."),
    P("Hỏi: Nếu ngày đầu của tôi không phải Thứ Hai thì sao? Đáp: HR Onboarding thông báo lịch dời tương ứng trong Thư tiếp nhận."),
    P("Hỏi: Tôi vắng buổi đào tạo an toàn thông tin thì sao? Đáp: Báo HR Onboarding để được sắp xếp buổi bù."),

    H1("Lịch sử sửa đổi"),
    T(["Phiên bản", "Ngày", "Nội dung thay đổi"], [
        ["1.0", "2025-09-01", "Ban hành lịch tuần đầu tiên kèm hướng dẫn chuẩn bị, kỳ vọng và mẫu phiếu phản hồi."],
    ], widths=[2.4, 3, 7.6]),
]


# =====================================================================================================================
# P03 Chương trình Mentor và Buddy
# =====================================================================================================================
_P03 = [
    H1("Thông tin kiểm soát tài liệu"),
    T(["Hạng mục", "Nội dung"], [
        ["Mã tài liệu", "SYN-P03"],
        ["Tên tài liệu", "Chương trình Mentor và Buddy"],
        ["Phiên bản", "1.0"],
        ["Đơn vị sở hữu", _HR],
        ["Người phê duyệt", "Trưởng phòng Nhân sự"],
        ["Đối tượng áp dụng", "Nhân sự mới, Mentor, Buddy, quản lý trực tiếp, đầu mối bộ phận"],
        ["Phân loại", "Nội bộ"],
        ["Ghi chú", _NOTE],
    ], widths=[4, 9]),

    H1("Mục đích, phạm vi và đối tượng"),
    P("Chương trình Mentor và Buddy giúp nhân sự mới hòa nhập nhanh và đúng hướng bằng cách bố trí hai người đồng hành với hai vai trò khác nhau. Một người lo về chuyên môn và nghề nghiệp, "
      "một người lo về văn hóa và những việc nhỏ hằng ngày. Việc tách hai vai trò giúp nhân sự mới biết chính xác nên hỏi ai trong từng tình huống và tránh dồn mọi kỳ vọng lên quản lý trực tiếp."),
    P("Tài liệu áp dụng cho mọi nhân sự mới của công ty tại các văn phòng. Tài liệu mô tả sự khác nhau giữa hai vai trò, quy tắc phân công, thời gian đồng hành, cách nhân sự mới biết người được phân công "
      "và cách xử lý khi có thay đổi. Tài liệu không chứa thông tin về bất kỳ cá nhân cụ thể nào. Danh sách phân công được gửi riêng cho từng nhân sự qua thư."),
    H2("Tài liệu liên quan"),
    B("Hướng dẫn ngày đầu đi làm: mốc gặp Buddy trong ngày đầu tiên.",
      "Lịch tuần đầu tiên của nhân sự mới: buổi gặp Mentor vào Thứ Tư và buổi tổng kết với Buddy vào Thứ Sáu.",
      "Danh bạ đầu mối theo đội: kênh liên hệ HR Onboarding.",
      "Quy trình nhận chỗ ngồi và đổi chỗ ngồi: Buddy có thể hỗ trợ nhân sự mới làm quen khu vực ngồi."),

    H1("Định nghĩa và thuật ngữ"),
    T(["Thuật ngữ", "Ý nghĩa"], [
        ["Mentor", "Nhân viên cấp Senior trở lên, không phải quản lý trực tiếp, hỗ trợ chuyên môn kỹ thuật và định hướng nghề nghiệp."],
        ["Buddy", "Nhân viên cùng bộ phận, có thâm niên từ 6 tháng, hỗ trợ văn hóa và hòa nhập cho nhân sự mới."],
        ["Quản lý trực tiếp", "Người giao việc, đánh giá công việc và phê duyệt nghỉ phép của nhân sự mới."],
        ["Thư giới thiệu đội", "Thư gửi nhân sự mới, giới thiệu đội và ghi danh sách phân công Mentor, Buddy."],
        ["Đầu mối bộ phận", "Người của bộ phận làm việc với HR Onboarding về tiếp nhận và phân công."],
        ["Thời gian đồng hành", "Khoảng thời gian Mentor hoặc Buddy chính thức hỗ trợ nhân sự mới."],
        ["Phân công", "Việc chỉ định Mentor và Buddy cho từng nhân sự mới."],
    ], widths=[3.4, 9.6]),

    H1("Vai trò và trách nhiệm"),
    T(["Vai trò", "Trách nhiệm chính", "Ghi chú"], [
        ["HR Onboarding", "Điều phối phân công, gửi Thư giới thiệu đội, giải quyết thắc mắc", "Đầu mối duy nhất xác nhận danh sách"],
        ["Quản lý trực tiếp", "Đề xuất ứng viên phù hợp, xác nhận thông tin phân công", "Không được làm Mentor hoặc Buddy"],
        ["Mentor", "Định hướng chuyên môn, nghề nghiệp, nhận xét về tiến bộ kỹ thuật", "Đồng hành trong 6 tháng đầu"],
        ["Buddy", "Giúp làm quen văn hóa, quy trình hằng ngày, đồng nghiệp", "Hỗ trợ trong 3 tháng đầu"],
        ["Nhân sự mới", "Chủ động hỏi, giữ liên lạc, phản hồi về chương trình", "Không chờ bị động"],
        ["Đầu mối bộ phận", "Đề xuất Buddy trong đội, báo thay đổi cho HR Onboarding", "Trước ngày đầu tiên"],
    ], widths=[3, 6.5, 3.5]),

    H1("Quy trình chi tiết"),
    H2("Phân biệt Mentor và Buddy"),
    P("Mentor hỗ trợ chuyên môn kỹ thuật và định hướng nghề nghiệp. Mentor là nhân viên cấp Senior trở lên, không phải quản lý trực tiếp. Buddy hỗ trợ văn hóa và hòa nhập, giúp nhân sự mới làm quen môi trường "
      "và quy trình hằng ngày. Buddy là nhân viên cùng bộ phận, có thâm niên từ 6 tháng."),
    T(["Tiêu chí", "Mentor", "Buddy"], [
        ["Trọng tâm", "Chuyên môn kỹ thuật, định hướng nghề nghiệp", "Văn hóa, hòa nhập, quy trình hằng ngày"],
        ["Cấp bậc", "Senior trở lên", "Không quy định cấp bậc tối thiểu"],
        ["Bộ phận", "Theo phân công của HR Onboarding", "Cùng bộ phận với nhân sự mới"],
        ["Thâm niên", "Thuộc cấp Senior trở lên", "Từ 6 tháng"],
        ["Thời gian đồng hành", "6 tháng đầu", "3 tháng đầu"],
        ["Quan hệ với quản lý", "Không phải quản lý trực tiếp", "Không phải quản lý trực tiếp"],
    ], widths=[3, 5, 5]),

    H2("Quy tắc phân công"),
    N("Mentor và Buddy phải là hai người khác nhau. Không được dùng một người cho cả hai vai trò dù người đó đáp ứng đủ điều kiện.",
      "Quản lý trực tiếp không được làm Mentor hoặc Buddy của nhân sự mình quản lý. Quản lý chỉ xác nhận thông tin phân công.",
      "Buddy phải cùng bộ phận và có thâm niên từ 6 tháng để đủ hiểu quy trình của đội.",
      "Mentor phải từ cấp Senior trở lên để có đủ kinh nghiệm chuyên môn.",
      "Không phân công một người làm Buddy cho quá nhiều nhân sự mới cùng lúc để bảo đảm chất lượng hỗ trợ.",
      "Việc phân công phải được HR Onboarding ghi nhận thì mới có hiệu lực."),

    H2("Cách biết Mentor và Buddy của mình"),
    P("Danh sách phân công Mentor và Buddy được gửi trong Thư giới thiệu đội chậm nhất 2 ngày làm việc trước ngày đầu tiên. Hệ thống chatbot không có dữ liệu phân công cá nhân, "
      "vì vậy chatbot không thể cho biết ai là Mentor hoặc Buddy của một nhân sự cụ thể. Chatbot chỉ hướng dẫn cách tìm thông tin."),
    P("Nếu chưa nhận được thư, nhân sự liên hệ đầu mối HR Onboarding qua hr-onboarding@vsf-demo.example để được xác nhận. Nhân sự không nhờ quản lý trực tiếp làm Mentor hoặc Buddy; "
      "quản lý chỉ xác nhận thông tin phân công do HR Onboarding cung cấp. Nếu HR Onboarding cần thêm thông tin, HR Onboarding sẽ xác nhận lại với đầu mối bộ phận."),

    H2("Thời gian đồng hành"),
    T(["Giai đoạn", "Mentor", "Buddy"], [
        ["Trước ngày đầu tiên", "Nhận thông tin về nhân sự mới", "Nhận thông tin và lịch gặp ngày đầu"],
        ["Ngày đầu tiên", "Chưa cần gặp", "Gặp nhân sự mới tại khu vực làm việc của đội"],
        ["Tuần đầu tiên", "Gặp vào Thứ Tư, thống nhất mục tiêu tháng đầu", "Đồng hành cả tuần, tổng kết vào Thứ Sáu"],
        ["3 tháng đầu", "Tiếp tục định hướng chuyên môn", "Hỗ trợ hòa nhập, kết thúc vai trò chính thức khi hết 3 tháng"],
        ["6 tháng đầu", "Đồng hành đến hết 6 tháng", "Không còn vai trò chính thức, vẫn là đồng nghiệp thân thiện"],
    ], widths=[2.8, 5, 5.2]),
    P("Buddy hỗ trợ trong 3 tháng đầu. Mentor đồng hành trong 6 tháng đầu. Sau khi hết thời gian này, nhân sự vẫn có thể liên hệ với người từng đồng hành, nhưng đó không còn là trách nhiệm chính thức của chương trình."),

    H2("Hoạt động gợi ý trong chương trình"),
    B("Với Buddy: dẫn tham quan khu vực làm việc, giới thiệu đồng nghiệp, cùng ăn trưa lần đầu, chỉ cách dùng phòng họp và các công cụ chung, giải thích các quy ước bất thành văn của đội.",
      "Với Mentor: trao đổi về mục tiêu tháng đầu, rà soát tài liệu kỹ thuật cần đọc, góp ý cách tiếp cận vấn đề, chia sẻ lộ trình phát triển nghề nghiệp.",
      "Với nhân sự mới: ghi lại câu hỏi, chuẩn bị nội dung trước mỗi buổi gặp, phản hồi trung thực về mức độ hữu ích.",
      "Với quản lý trực tiếp: tạo điều kiện về thời gian, không can thiệp vào nội dung trao đổi riêng của nhân sự với Mentor hoặc Buddy."),

    H2("Bảo mật và giới hạn của vai trò"),
    P("Mentor và Buddy không được nhận danh nghĩa quản lý để giao việc hay đánh giá thử việc, không có quyền phê duyệt nghỉ phép hoặc cấp quyền hệ thống. Khi nhân sự mới cần những việc này, "
      "Mentor và Buddy hướng dẫn tới quản lý trực tiếp hoặc đội phụ trách. Thông tin cá nhân mà nhân sự mới chia sẻ trong quá trình trao đổi được giữ kín, trừ khi ảnh hưởng đến an toàn hoặc tuân thủ."),

    H2("Cách tổ chức một buổi gặp hiệu quả"),
    P("Dù là buổi gặp với Mentor hay với Buddy, nhân sự mới và người đồng hành nên thống nhất trước về mục tiêu của buổi, thời lượng dự kiến và cách ghi lại kết quả. "
      "Buổi gặp nên bắt đầu bằng việc nhìn lại những gì đã diễn ra kể từ lần trước, sau đó đi vào một hoặc hai chủ đề chính thay vì cố gắng nói về mọi vấn đề cùng lúc. "
      "Cuối buổi, hai bên nhắc lại các việc cần làm tiếp theo và hẹn thời điểm trao đổi sau."),
    B("Buổi gặp với Mentor thiên về nội dung: kiến thức chuyên môn cần bổ sung, cách tiếp cận một bài toán, cách đọc mã nguồn hoặc tài liệu của đội, định hướng học tập và phát triển nghề nghiệp.",
      "Buổi gặp với Buddy thiên về trải nghiệm: cách đội phối hợp hằng ngày, kênh trao đổi nào dùng cho việc gì, những điều nên và không nên làm ở nơi làm việc, cảm nhận của nhân sự mới về môi trường.",
      "Nhân sự mới nên ghi chú và chủ động gửi lại tóm tắt ngắn sau buổi gặp để hai bên cùng hiểu như nhau.",
      "Nếu một vấn đề vượt quá phạm vi của Mentor hoặc Buddy, hai bên cùng xác định đầu mối phù hợp như quản lý trực tiếp, IT Helpdesk hoặc HR Onboarding."),

    H2("Theo dõi và phản hồi về chương trình"),
    P("HR Onboarding theo dõi chương trình bằng cách thu thập phản hồi của nhân sự mới, Mentor và Buddy vào các thời điểm thuận tiện, đặc biệt là sau tuần đầu tiên và khi kết thúc thời gian đồng hành của từng vai trò. "
      "Phản hồi được dùng để cải thiện việc chọn người, tài liệu hướng dẫn và cách phối hợp giữa các đội. Phản hồi về từng cá nhân được xử lý kín đáo và không ảnh hưởng đến đánh giá công việc của nhân sự mới."),

    H2("Thay đổi hoặc kết thúc phân công"),
    N("Khi Mentor hoặc Buddy không thể tiếp tục vì nghỉ dài ngày, chuyển đội hoặc thay đổi công việc, người đó báo ngay cho HR Onboarding.",
      "Khi nhân sự mới thấy chưa phù hợp, gửi phản hồi cho HR Onboarding hoặc quản lý trực tiếp. Mọi phản hồi được xử lý kín đáo.",
      "HR Onboarding xem xét và chỉ định người thay thế đáp ứng các điều kiện của chương trình.",
      "HR Onboarding gửi thư xác nhận cho nhân sự mới và cho người mới được phân công.",
      "Thay đổi không làm thay đổi tổng thời gian đồng hành của vai trò tương ứng."),

    H2("Mẫu email hỏi về phân công"),
    P("Kính gửi HR Onboarding, tôi sắp bắt đầu làm việc và chưa nhận được Thư giới thiệu đội có danh sách phân công Mentor và Buddy. Nhờ HR Onboarding xác nhận giúp tôi. Trân trọng."),
    H2("Mẫu email cảm ơn và phản hồi cuối giai đoạn"),
    P("Kính gửi HR Onboarding, tôi xin phản hồi về chương trình. Điều tôi thấy hữu ích nhất là [nội dung ngắn gọn]. Điều tôi mong được cải thiện là [nội dung ngắn gọn]. Xin cảm ơn."),

    H2("Checklist"),
    B("Nhân sự mới: đã nhận Thư giới thiệu đội, đã biết Mentor và Buddy của mình, đã có lịch gặp Buddy ngày đầu và lịch gặp Mentor.",
      "Buddy: đã biết ngày đầu của nhân sự mới, đã chuẩn bị giới thiệu đội, đã biết đầu mối HR Onboarding.",
      "Mentor: đã chuẩn bị nội dung cho buổi thống nhất mục tiêu tháng đầu.",
      "Quản lý trực tiếp: đã xác nhận thông tin phân công và không tự nhận làm Mentor hay Buddy."),

    H1("Trường hợp đặc biệt và ngoại lệ"),
    T(["Tình huống", "Nguyên nhân", "Cách xử lý"], [
        ["Chưa nhận Thư giới thiệu đội", "Thư chưa gửi hoặc vào thư rác", "Liên hệ HR Onboarding để được xác nhận"],
        ["Đội chưa có ai thâm niên từ 6 tháng để làm Buddy", "Đội mới thành lập", "Đầu mối bộ phận báo HR Onboarding để xem xét và thông báo cho nhân sự mới"],
        ["Chưa có ai đủ cấp Senior làm Mentor", "Thiếu nhân sự cấp Senior", "Đầu mối bộ phận báo HR Onboarding để xem xét và thông báo cho nhân sự mới"],
        ["Quản lý muốn làm Mentor", "Muốn trực tiếp hướng dẫn", "Không được phép, quản lý trực tiếp không làm Mentor hoặc Buddy"],
        ["Mentor và Buddy trùng một người", "Sắp xếp nhầm", "Không hợp lệ, HR Onboarding phân công lại một trong hai vai trò"],
        ["Nhân sự mới muốn đổi Mentor hoặc Buddy", "Chưa phù hợp", "Gửi phản hồi tới HR Onboarding"],
    ], widths=[4, 3.6, 5.4]),

    H1("Câu hỏi thường gặp"),
    P("Hỏi: Mentor và Buddy khác nhau thế nào? Đáp: Mentor hỗ trợ chuyên môn kỹ thuật và định hướng nghề nghiệp, còn Buddy hỗ trợ văn hóa và hòa nhập; hai người khác nhau."),
    P("Hỏi: Ai được làm Mentor? Đáp: Nhân viên cấp Senior trở lên, không phải quản lý trực tiếp."),
    P("Hỏi: Ai được làm Buddy? Đáp: Nhân viên cùng bộ phận, có thâm niên từ 6 tháng."),
    P("Hỏi: Buddy hỗ trợ tôi bao lâu? Đáp: Trong 3 tháng đầu."),
    P("Hỏi: Mentor đồng hành bao lâu? Đáp: Trong 6 tháng đầu."),
    P("Hỏi: Quản lý trực tiếp của tôi có thể là Mentor hoặc Buddy không? Đáp: Không, quản lý trực tiếp không được làm Mentor hoặc Buddy."),
    P("Hỏi: Khi nào tôi biết Mentor và Buddy của mình? Đáp: Trong Thư giới thiệu đội, gửi chậm nhất 2 ngày làm việc trước ngày đầu tiên."),
    P("Hỏi: Chatbot có cho tôi biết Mentor của tôi là ai không? Đáp: Không, chatbot không có dữ liệu phân công cá nhân."),
    P("Hỏi: Tôi chưa nhận thư thì làm gì? Đáp: Liên hệ đầu mối HR Onboarding để được xác nhận."),
    P("Hỏi: Một người có thể vừa là Mentor vừa là Buddy của tôi không? Đáp: Không, hai vai trò phải do hai người khác nhau đảm nhiệm."),

    H1("Lịch sử sửa đổi"),
    T(["Phiên bản", "Ngày", "Nội dung thay đổi"], [
        ["1.0", "2024-06-01", "Ban hành chương trình Mentor và Buddy, gồm vai trò, quy tắc phân công, thời gian đồng hành và cách biết người được phân công."],
    ], widths=[2.4, 3, 7.6]),
]


# =====================================================================================================================
# P04 Quy trình nhận chỗ ngồi và đổi chỗ ngồi
# =====================================================================================================================
_P04 = [
    H1("Thông tin kiểm soát tài liệu"),
    T(["Hạng mục", "Nội dung"], [
        ["Mã tài liệu", "SYN-P04"],
        ["Tên tài liệu", "Quy trình nhận chỗ ngồi và đổi chỗ ngồi"],
        ["Phiên bản", "1.1"],
        ["Đơn vị sở hữu", _FAC],
        ["Người phê duyệt", "Trưởng ban Hành chính - Cơ sở vật chất"],
        ["Đối tượng áp dụng", "Nhân sự mới và nhân sự đang làm việc tại các văn phòng"],
        ["Phân loại", "Nội bộ"],
        ["Ghi chú", _NOTE],
    ], widths=[4, 9]),

    H1("Mục đích, phạm vi và đối tượng"),
    P("Quy trình này quy định cách nhân sự mới biết chỗ ngồi ban đầu trước và trong ngày đầu tiên, và cách nhân sự đề nghị đổi chỗ ngồi sau đó. Mục tiêu là mỗi nhân sự có một vị trí làm việc rõ ràng từ lúc bước vào văn phòng, "
      "và mọi thay đổi vị trí đều đi qua một đầu mối để Ban Hành chính nắm được tình hình sử dụng không gian."),
    P("Phạm vi gồm việc thông báo chỗ ngồi ban đầu, việc đưa nhân sự tới vị trí trong ngày đầu tiên và việc đổi chỗ ngồi bằng form FAC-01. Quy trình không bao gồm việc cấp thiết bị (xem Hướng dẫn cấp phát và cấu hình thiết bị), "
      "thẻ từ và thẻ xe (xem Hướng dẫn nhận thẻ từ và đăng ký thẻ xe). Tài liệu không nêu vị trí ngồi của bất kỳ cá nhân nào; chatbot cũng không có dữ liệu này."),
    H2("Tài liệu liên quan"),
    B("Hướng dẫn ngày đầu đi làm: lịch ngày đầu, trong đó có việc được dẫn tới vị trí ngồi.",
      "Danh bạ đầu mối theo đội: kênh liên hệ HR Onboarding, Facilities và Quầy tiếp nhận.",
      "Hướng dẫn nhận thẻ từ và đăng ký thẻ xe: thẻ từ cần thiết để vào khu vực làm việc.",
      "Chương trình Mentor và Buddy: Buddy hỗ trợ nhân sự mới làm quen khu vực làm việc."),

    H1("Định nghĩa và thuật ngữ"),
    T(["Thuật ngữ", "Ý nghĩa"], [
        ["Thư tiếp nhận", "Thư do đầu mối bộ phận gửi trước ngày đầu tiên, trong đó ghi vị trí ngồi."],
        ["Vị trí ngồi", "Bàn làm việc được phân cho nhân sự, ghi trong Thư tiếp nhận."],
        ["Quầy tiếp nhận", "Điểm đón nhân sự mới, nơi báo họ tên và bộ phận để được dẫn tới vị trí."],
        ["Đầu mối bộ phận", "Người của bộ phận phụ trách gửi Thư tiếp nhận và làm việc với HR Onboarding."],
        ["Cổng Facilities", "Cổng yêu cầu của Facilities, nơi gửi form FAC-01 và FAC-02."],
        ["FAC-01", "Form yêu cầu đổi chỗ ngồi trên cổng Facilities."],
        ["Hàng đợi", "Danh sách yêu cầu chờ xử lý của Ban Hành chính."],
        ["Ngày làm việc", "Ngày làm việc theo lịch của công ty, không tính ngày nghỉ."],
    ], widths=[3.4, 9.6]),

    H1("Vai trò và trách nhiệm"),
    T(["Vai trò", "Trách nhiệm"], [
        ["Đầu mối bộ phận", "Xác định vị trí ngồi cho nhân sự mới và gửi Thư tiếp nhận trước ngày đầu tiên."],
        ["Quản lý trực tiếp", "Xác nhận thông tin vị trí ngồi, đồng ý hoặc không đồng ý với nhu cầu đổi chỗ."],
        ["HR Onboarding", "Hỗ trợ khi nhân sự chưa có thông tin chỗ ngồi, liên hệ đầu mối bộ phận để xác nhận."],
        ["Quầy tiếp nhận", "Đón nhân sự, ghi nhận họ tên và bộ phận, dẫn tới vị trí đã ghi trong thư. Không quyết định vị trí ngồi."],
        ["Facilities (Ban Hành chính)", "Xử lý yêu cầu đổi chỗ ngồi trong 3 ngày làm việc và cập nhật sơ đồ chỗ ngồi."],
        ["Nhân sự mới", "Đọc Thư tiếp nhận, báo khi thiếu thông tin, dùng form FAC-01 khi cần đổi."],
    ], widths=[3.8, 9.2]),

    H1("Quy trình chi tiết"),
    H2("Nhận chỗ ngồi ban đầu"),
    N("Kiểm tra Thư tiếp nhận do đầu mối bộ phận gửi trước ngày đầu tiên, trong đó ghi vị trí ngồi.",
      "Nếu chưa có thông tin, liên hệ đầu mối HR Onboarding theo Danh bạ đầu mối.",
      "Khi đến nơi, báo họ tên và bộ phận tại Quầy tiếp nhận để được dẫn tới vị trí."),
    P("Sau đây là mô tả chi tiết từng bước."),
    H2("Bước 1: kiểm tra Thư tiếp nhận"),
    P("Nhân sự mở hộp thư email đăng ký và tìm Thư tiếp nhận. Thư ghi rõ vị trí ngồi và một số thông tin cần thiết khác cho ngày đầu. Nhân sự nên đọc thư ít nhất một lần trước ngày đầu tiên, "
      "ghi lại vị trí ngồi và kiểm tra xem tên bộ phận trong thư có đúng với thư nhận việc hay không. Nếu thấy khác biệt, báo ngay cho HR Onboarding thay vì tự suy đoán."),
    H2("Bước 2: liên hệ HR Onboarding khi chưa có thông tin"),
    P("Nếu không tìm thấy Thư tiếp nhận hoặc thư không nêu vị trí ngồi, nhân sự gửi email tới hr-onboarding@vsf-demo.example, nêu họ tên, bộ phận và ngày đầu tiên. "
      "HR Onboarding xác nhận với đầu mối bộ phận và trả lời cho nhân sự. Nếu vẫn chưa có thông tin sau khi liên hệ HR Onboarding, nhân sự hỏi lại đầu mối bộ phận hoặc quản lý trực tiếp."),
    H2("Bước 3: báo họ tên và bộ phận tại Quầy tiếp nhận"),
    P("Trong ngày đầu tiên, khi đến văn phòng, nhân sự báo họ tên và bộ phận tại Quầy tiếp nhận. Nhân viên tiếp nhận đối chiếu với thông tin đã có và dẫn nhân sự tới vị trí. "
      "Quầy tiếp nhận không quyết định vị trí ngồi; nếu nhân sự thấy vị trí khác với thư, nhân sự báo cho quản lý trực tiếp và HR Onboarding chứ không tự chuyển sang bàn khác."),
    T(["Mốc", "Việc phải làm", "Người thực hiện"], [
        ["Trước ngày đầu tiên", "Gửi Thư tiếp nhận có vị trí ngồi", "Đầu mối bộ phận"],
        ["Trước ngày đầu tiên", "Đọc thư và ghi lại vị trí", "Nhân sự mới"],
        ["Khi chưa có thông tin", "Email HR Onboarding", "Nhân sự mới"],
        ["Ngày đầu tiên", "Báo họ tên và bộ phận tại Quầy tiếp nhận", "Nhân sự mới"],
        ["Ngày đầu tiên", "Dẫn tới vị trí đã ghi trong thư", "Quầy tiếp nhận"],
    ], widths=[3.6, 6.2, 3.2]),

    H2("Đổi chỗ ngồi sau đó"),
    P("Nhân sự muốn đổi chỗ ngồi tạo yêu cầu bằng form FAC-01 trên cổng Facilities. Yêu cầu được chuyển vào hàng đợi của Ban Hành chính và xử lý trong 3 ngày làm việc. "
      "Cổng Facilities nằm tại https://facilities.vsf-demo.example/requests."),
    N("Trao đổi trước với quản lý trực tiếp để bảo đảm việc đổi chỗ không ảnh hưởng đến công việc của đội.",
      "Mở cổng Facilities và chọn form FAC-01.",
      "Điền mã nhân viên, vị trí hiện tại (không bắt buộc), vị trí mong muốn và lý do.",
      "Gửi yêu cầu. Yêu cầu vào hàng đợi của Ban Hành chính.",
      "Chờ Facilities xử lý trong 3 ngày làm việc. Trong thời gian này, tiếp tục ngồi tại vị trí hiện tại.",
      "Khi có xác nhận vị trí mới, chuyển đồ cá nhân và báo cho Buddy hoặc đồng nghiệp cùng đội nếu cần."),
    T(["Trường của FAC-01", "Bắt buộc", "Cách điền"], [
        ["Mã nhân viên", "Có", "Mã được cấp khi vào làm"],
        ["Vị trí hiện tại", "Không", "Khu vực hoặc tầng đang ngồi, không ghi số bàn nếu không chắc"],
        ["Vị trí mong muốn", "Có", "Khu vực, tầng hoặc đội mong muốn"],
        ["Lý do", "Có", "Nêu ngắn gọn, ví dụ để gần đội, vì lý do sức khỏe hoặc ánh sáng"],
    ], widths=[3.6, 2.4, 7]),

    H2("Cam kết thời gian"),
    T(["Hạng mục", "Thời hạn", "Đơn vị"], [
        ["Gửi Thư tiếp nhận", "Trước ngày đầu tiên", "Đầu mối bộ phận"],
        ["HR Onboarding phản hồi khi nhân sự chưa có thông tin", "Theo giờ hỗ trợ ghi trong Danh bạ đầu mối", "HR Onboarding"],
        ["Xử lý yêu cầu FAC-01", "3 ngày làm việc", "Facilities"],
    ], widths=[6.5, 4, 2.5]),

    H1("Trường hợp đặc biệt và ngoại lệ"),
    T(["Tình huống", "Nguyên nhân", "Cách xử lý"], [
        ["Chưa nhận được Thư tiếp nhận", "Thư chưa gửi hoặc vào thư rác", "Kiểm tra thư rác, liên hệ HR Onboarding"],
        ["Vị trí ghi trong thư đã có người ngồi", "Nhầm lẫn hoặc thay đổi phút chót", "Không tự chuyển bàn; báo Quầy tiếp nhận, quản lý và HR Onboarding"],
        ["Thiết bị hoặc bàn ghế ở vị trí bị hỏng", "Hao mòn", "Báo Facilities qua email hoặc cổng Facilities"],
        ["Cần vị trí phù hợp vì lý do sức khỏe", "Nhu cầu cá nhân", "Nêu trong FAC-01 hoặc trao đổi riêng với HR Onboarding"],
        ["Bộ phận chuyển khu vực", "Thay đổi tổ chức", "Đầu mối bộ phận thông báo cho Facilities và HR Onboarding"],
        ["Yêu cầu FAC-01 chưa có phản hồi", "Đang trong hàng đợi", "Chờ đủ 3 ngày làm việc rồi liên hệ facilities@vsf-demo.example"],
        ["Muốn đổi ngay trong ngày đầu", "Chưa quen khu vực", "Trao đổi với quản lý, sau đó tạo FAC-01 như bình thường"],
    ], widths=[4.2, 3.4, 5.4]),

    H2("Lỗi thường gặp và cách xử lý"),
    B("Nhân sự hỏi Quầy tiếp nhận để xin đổi chỗ ngay: Quầy tiếp nhận không quyết định vị trí ngồi, hướng dẫn nhân sự dùng form FAC-01.",
      "Nhân sự gửi FAC-01 nhiều lần cho cùng một nhu cầu: chỉ cần một yêu cầu, gửi lại nhiều lần có thể làm chậm xử lý.",
      "Nhân sự ghi vị trí mong muốn quá chung chung: nên nêu khu vực hoặc đội cụ thể.",
      "Nhân sự tự chuyển bàn khi chờ: không được phép, cần chờ xác nhận của Facilities."),

    H1("Checklist và mẫu thông báo"),
    H2("Checklist cho nhân sự mới"),
    B("Đã đọc Thư tiếp nhận và biết vị trí ngồi.",
      "Đã biết Quầy tiếp nhận của văn phòng mình.",
      "Đã biết cách liên hệ HR Onboarding khi thiếu thông tin.",
      "Đã biết đổi chỗ ngồi sau đó phải dùng form FAC-01."),
    H2("Checklist cho đầu mối bộ phận"),
    B("Đã xác định vị trí ngồi cho nhân sự mới.",
      "Đã gửi Thư tiếp nhận trước ngày đầu tiên.",
      "Đã thông báo cho Facilities nếu cần chuẩn bị thêm bàn ghế."),
    H2("Mẫu email hỏi vị trí ngồi"),
    P("Kính gửi HR Onboarding, tôi sẽ bắt đầu làm việc vào [ngày đầu tiên] tại bộ phận [tên bộ phận] và chưa nhận được thông tin vị trí ngồi trong Thư tiếp nhận. Nhờ HR Onboarding xác nhận giúp tôi. Trân trọng."),
    H2("Mẫu nội dung lý do trong FAC-01"),
    P("Tôi đề nghị chuyển sang khu vực gần đội [tên đội] để thuận lợi trao đổi công việc hằng ngày. Quản lý trực tiếp đã đồng ý."),

    H1("Câu hỏi thường gặp"),
    P("Hỏi: Tôi biết chỗ ngồi của mình ở đâu? Đáp: Xem Thư tiếp nhận do đầu mối bộ phận gửi trước ngày đầu tiên, trong đó ghi vị trí ngồi."),
    P("Hỏi: Nếu chưa có thông tin thì sao? Đáp: Liên hệ đầu mối HR Onboarding theo Danh bạ đầu mối."),
    P("Hỏi: Ngày đầu tôi làm gì để được dẫn tới chỗ ngồi? Đáp: Báo họ tên và bộ phận tại Quầy tiếp nhận."),
    P("Hỏi: Quầy tiếp nhận có xếp chỗ cho tôi không? Đáp: Không, Quầy tiếp nhận chỉ dẫn tới vị trí đã ghi trong thư."),
    P("Hỏi: Tôi muốn đổi chỗ ngồi thì làm sao? Đáp: Tạo yêu cầu bằng form FAC-01 trên cổng Facilities."),
    P("Hỏi: Đổi chỗ ngồi mất bao lâu? Đáp: Yêu cầu được xử lý trong 3 ngày làm việc."),
    P("Hỏi: Chatbot có cho tôi biết chỗ ngồi không? Đáp: Không, chatbot không có dữ liệu chỗ ngồi cá nhân."),
    P("Hỏi: Trường nào trong FAC-01 không bắt buộc? Đáp: Vị trí hiện tại."),
    P("Hỏi: Tôi có được tự chuyển bàn khi chờ xử lý không? Đáp: Không, cần chờ xác nhận của Facilities."),
    P("Hỏi: Yêu cầu FAC-01 đi vào đâu? Đáp: Vào hàng đợi của Ban Hành chính."),

    H1("Lịch sử sửa đổi"),
    T(["Phiên bản", "Ngày", "Nội dung thay đổi"], [
        ["1.0", "2025-01-15", "Ban hành quy trình nhận chỗ ngồi ban đầu."],
        ["1.1", "2025-05-01", "Bổ sung quy trình đổi chỗ ngồi bằng form FAC-01 và làm rõ vai trò của Quầy tiếp nhận."],
    ], widths=[2.4, 3, 7.6]),
]


# =====================================================================================================================
# P05 Danh bạ đầu mối theo đội
# =====================================================================================================================
_P05 = [
    H1("Thông tin kiểm soát tài liệu"),
    T(["Hạng mục", "Nội dung"], [
        ["Mã tài liệu", "SYN-P05"],
        ["Tên tài liệu", "Danh bạ đầu mối theo đội"],
        ["Phiên bản", "2.0"],
        ["Đơn vị sở hữu", _HR],
        ["Người phê duyệt", "Trưởng phòng Nhân sự"],
        ["Đối tượng áp dụng", "Toàn bộ nhân sự, đặc biệt nhân sự mới"],
        ["Phân loại", "Nội bộ"],
        ["Ghi chú", _NOTE],
    ], widths=[4, 9]),

    H1("Mục đích, phạm vi và đối tượng"),
    P("Danh bạ này giúp nhân sự, nhất là nhân sự mới, biết nên liên hệ đội nào cho từng loại việc và qua kênh nào. Mục tiêu là rút ngắn thời gian tìm người xử lý, "
      "tránh gửi yêu cầu nhầm nơi và bảo đảm những việc gấp, đặc biệt là sự cố bảo mật, đến đúng đầu mối ngay từ đầu."),
    P("Danh bạ chỉ nêu đầu mối theo đội, không nêu tên hay số điện thoại cá nhân. Khi cần trao đổi với một người cụ thể, nhân sự hỏi thông qua đầu mối của đội hoặc quản lý trực tiếp. "
      "Các địa chỉ email và cổng trong tài liệu là giả lập; chỉ những kênh ghi trong danh bạ này mới được dùng làm kênh chính thức."),
    H2("Tài liệu liên quan"),
    B("Hướng dẫn ngày đầu đi làm: nơi và cách làm việc với Quầy tiếp nhận trong ngày đầu tiên.",
      "Chương trình Mentor và Buddy: liên hệ HR Onboarding khi chưa nhận thông tin phân công.",
      "Quy trình nhận chỗ ngồi và đổi chỗ ngồi: liên hệ HR Onboarding và Facilities về chỗ ngồi.",
      "Hướng dẫn nhận thẻ từ và đăng ký thẻ xe: liên hệ Facilities về thẻ.",
      "Hướng dẫn cấp phát và cấu hình thiết bị: liên hệ IT Helpdesk về thiết bị.",
      "Quy trình yêu cầu cài phần mềm và kiểm tra VinSOC: yêu cầu VinSOC đi qua IT Helpdesk.",
      "Quy trình báo cáo sự cố bảo mật: báo Trực SOC khi có sự cố."),

    H1("Định nghĩa và thuật ngữ"),
    T(["Thuật ngữ", "Ý nghĩa"], [
        ["Đầu mối", "Đội hoặc kênh được chỉ định tiếp nhận yêu cầu về một nhóm vấn đề."],
        ["Giờ hỗ trợ", "Khung giờ đầu mối tiếp nhận và xử lý yêu cầu."],
        ["Giờ hành chính", "Khung giờ làm việc hành chính thông thường của công ty."],
        ["Cổng", "Trang web nội bộ để gửi yêu cầu theo form, ví dụ cổng IT và cổng Facilities."],
        ["HR Portal", "Cổng nhân sự dùng cho các việc như đăng ký nghỉ phép."],
        ["Trực SOC", "Kênh trực 24/7 dành riêng cho sự cố bảo mật."],
        ["Leo thang", "Chuyển vấn đề lên cấp cao hơn khi đầu mối chưa xử lý được."],
    ], widths=[3.4, 9.6]),

    H1("Vai trò và trách nhiệm"),
    T(["Vai trò", "Trách nhiệm"], [
        ["Nhân sự", "Chọn đúng đầu mối, cung cấp đủ thông tin, dùng kênh chính thức trong danh bạ."],
        ["Đầu mối của đội", "Xác nhận đã nhận yêu cầu, xử lý theo thời hạn và chuyển đúng đội khi yêu cầu không thuộc phạm vi."],
        ["HR Onboarding", "Duy trì danh bạ, cập nhật khi có thay đổi kênh liên hệ."],
        ["Quản lý trực tiếp", "Hỗ trợ leo thang khi đầu mối chưa phản hồi."],
    ], widths=[3.4, 9.6]),

    H1("Quy trình chi tiết"),
    H2("Danh bạ đầu mối hỗ trợ"),
    T(["Đội", "Phụ trách", "Kênh liên hệ", "Giờ hỗ trợ"], [
        ["HR Onboarding", "Tiếp nhận, phân công Mentor/Buddy, chỗ ngồi ban đầu", "hr-onboarding@vsf-demo.example hoặc HR Portal", "8:30 - 17:30"],
        ["IT Helpdesk", "Thiết bị, tài khoản, VPN, phần mềm", "it-helpdesk@vsf-demo.example hoặc cổng IT", "8:00 - 18:00"],
        ["VinSOC", "Kiểm tra bảo mật, quét và duyệt link phần mềm", "Nhận yêu cầu qua IT Helpdesk, không nhận trực tiếp", "Giờ hành chính"],
        ["Trực SOC", "Sự cố bảo mật", "soc-oncall@vsf-demo.example", "24/7"],
        ["Facilities", "Chỗ ngồi, thẻ từ, thẻ xe", "facilities@vsf-demo.example hoặc cổng Facilities", "8:30 - 17:30"],
        ["Quầy tiếp nhận", "Đón nhân sự mới ngày đầu, phát thẻ từ", "Hà Nội: tầng 1 tòa TechnoPark. TP. Hồ Chí Minh: tầng trệt Vincom Center Đồng Khởi (địa điểm giả định)", "8:15 - 17:30"],
    ], widths=[2.2, 4.5, 5, 2.3]),
    P("Danh bạ này chỉ nêu đầu mối theo đội, không nêu tên hay số điện thoại cá nhân."),

    H2("Cổng và đường dẫn chính thức"),
    B("HR Portal: https://hr.vsf-demo.example, dùng cho các việc nhân sự như đăng ký nghỉ phép.",
      "Cổng IT: https://it.vsf-demo.example/requests, dùng để gửi yêu cầu cho IT Helpdesk.",
      "Cổng Facilities: https://facilities.vsf-demo.example/requests, dùng để gửi form FAC-01 và FAC-02."),

    H2("Khi nào liên hệ ai"),
    T(["Tình huống", "Liên hệ", "Kênh"], [
        ["Chưa nhận thư tiếp nhận hoặc Thư giới thiệu đội", "HR Onboarding", "Email hoặc HR Portal"],
        ["Chưa biết Mentor hoặc Buddy của mình", "HR Onboarding", "Email hoặc HR Portal"],
        ["Chưa có thông tin chỗ ngồi ban đầu", "HR Onboarding", "Email hoặc HR Portal"],
        ["Đổi chỗ ngồi sau đó", "Facilities", "Form FAC-01 trên cổng Facilities"],
        ["Thẻ từ hỏng hoặc mất", "Facilities", "Email hoặc cổng Facilities"],
        ["Đăng ký thẻ xe", "Facilities", "Form FAC-02 trên cổng Facilities"],
        ["Máy tính lỗi, cần cấu hình lại", "IT Helpdesk", "Cổng IT hoặc email"],
        ["Không kích hoạt được tài khoản hoặc không kết nối được VPN", "IT Helpdesk", "Email hoặc cổng IT"],
        ["Cần cài phần mềm ngoài danh mục", "IT Helpdesk", "Form yêu cầu cài phần mềm trên cổng IT"],
        ["Nghi ngờ mã độc, mất thiết bị, tài khoản bị chiếm quyền", "Trực SOC", "Email Trực SOC"],
        ["Cần VinSOC kiểm tra liên kết hoặc tệp cài đặt", "IT Helpdesk (chuyển tiếp VinSOC)", "Cổng IT"],
        ["Đến văn phòng ngày đầu và cần được dẫn đường", "Quầy tiếp nhận", "Trực tiếp tại văn phòng"],
    ], widths=[5.4, 3.6, 4]),

    H2("Nguyên tắc liên hệ VinSOC"),
    P("VinSOC không nhận yêu cầu trực tiếp từ nhân sự. Mọi yêu cầu kiểm tra bảo mật, quét và duyệt liên kết hoặc tệp cài đặt phần mềm được gửi qua IT Helpdesk, IT chuyển tới VinSOC. "
      "Riêng sự cố bảo mật khẩn cấp thì không đi qua IT Helpdesk mà báo trực tiếp cho Trực SOC."),
    H2("Nguyên tắc dùng Trực SOC"),
    P("Trực SOC hoạt động 24/7 và chỉ dành cho sự cố bảo mật như nghi ngờ mã độc, mất thiết bị hoặc tài khoản bị chiếm quyền. Các yêu cầu thông thường như quên mật khẩu, lỗi máy hoặc xin phần mềm "
      "không gửi cho Trực SOC mà gửi cho IT Helpdesk. Khi báo sự cố, nhân sự mô tả ngắn sự việc, thời điểm phát hiện và thiết bị liên quan, sau đó làm theo hướng dẫn của Trực SOC."),

    H2("Quy tắc leo thang"),
    N("Gửi yêu cầu tới đúng đầu mối và ghi lại thời điểm gửi, kênh đã dùng.",
      "Nếu quá thời hạn xử lý ghi trong quy trình tương ứng mà chưa có phản hồi, gửi nhắc lại một lần vào đúng email hoặc yêu cầu đã gửi.",
      "Nếu vẫn chưa có phản hồi, thông báo cho quản lý trực tiếp để quản lý làm việc với đầu mối bộ phận hoặc HR Onboarding.",
      "Với vấn đề liên quan đến nhân sự mới, HR Onboarding là đầu mối điều phối leo thang giữa các đội.",
      "Với sự cố bảo mật, không leo thang theo các bước trên mà báo Trực SOC ngay."),
    T(["Loại việc", "Cấp 1", "Cấp 2"], [
        ["Tiếp nhận, Mentor, Buddy, chỗ ngồi ban đầu", "HR Onboarding", "Đầu mối bộ phận và quản lý trực tiếp"],
        ["Thiết bị, tài khoản, VPN, phần mềm", "IT Helpdesk", "Quản lý trực tiếp"],
        ["Đổi chỗ, thẻ từ, thẻ xe", "Facilities", "HR Onboarding"],
        ["Sự cố bảo mật", "Trực SOC", "Theo hướng dẫn của Trực SOC"],
    ], widths=[5.6, 3.4, 4]),

    H2("Thông tin cần cung cấp khi liên hệ"),
    B("Họ tên, bộ phận và văn phòng làm việc.",
      "Mã nhân viên nếu đã được cấp, đặc biệt khi dùng form yêu cầu.",
      "Mô tả ngắn gọn vấn đề, thời điểm xảy ra và những gì đã thử.",
      "Không gửi mật khẩu, mã xác thực hoặc dữ liệu nhạy cảm qua email hay chat."),

    H1("Trường hợp đặc biệt và ngoại lệ"),
    T(["Tình huống", "Nguyên nhân", "Cách xử lý"], [
        ["Email gửi tới đầu mối bị trả lại", "Sai địa chỉ", "Đối chiếu với danh bạ này, không dùng địa chỉ cũ ngoài danh bạ"],
        ["Liên hệ ngoài giờ hỗ trợ", "Đầu mối chưa làm việc", "Gửi email, đầu mối xử lý khi bắt đầu giờ hỗ trợ; sự cố bảo mật thì báo Trực SOC"],
        ["Gửi yêu cầu VinSOC trực tiếp", "Chưa biết quy tắc", "Gửi lại qua IT Helpdesk"],
        ["Không rõ việc thuộc đội nào", "Việc liên quan nhiều đội", "Hỏi HR Onboarding để được điều phối"],
        ["Đầu mối không phản hồi", "Đang quá tải", "Nhắc lại một lần, sau đó leo thang theo quy tắc"],
        ["Cần liên hệ một cá nhân cụ thể", "Danh bạ không nêu tên", "Hỏi qua đầu mối của đội hoặc quản lý trực tiếp"],
    ], widths=[4, 3.4, 5.6]),

    H2("Lỗi thường gặp và cách xử lý"),
    B("Gửi mọi việc tới HR Onboarding: HR Onboarding chỉ lo tiếp nhận, phân công và chỗ ngồi ban đầu; việc thiết bị gửi IT Helpdesk.",
      "Báo lỗi máy tới Trực SOC: Trực SOC chỉ nhận sự cố bảo mật.",
      "Chờ mà không gửi yêu cầu chính thức: cần dùng form hoặc email theo danh bạ để có mã theo dõi.",
      "Gửi email tới địa chỉ cũ: chỉ dùng địa chỉ có trong danh bạ này."),

    H1("Checklist và mẫu thông báo"),
    H2("Checklist trước khi gửi yêu cầu"),
    B("Đã xác định đúng đội theo bảng khi nào liên hệ ai.",
      "Đã chọn kênh (email, cổng hoặc trực tiếp) phù hợp.",
      "Đã chuẩn bị mô tả vấn đề, mã nhân viên và các thông tin liên quan.",
      "Đã kiểm tra giờ hỗ trợ của đầu mối."),
    H2("Mẫu email gửi IT Helpdesk"),
    P("Kính gửi IT Helpdesk, tôi là nhân sự mới của bộ phận [tên bộ phận]. Tôi gặp lỗi [mô tả ngắn] trên thiết bị được cấp. Tôi đã thử [các bước đã thử]. Nhờ IT Helpdesk hỗ trợ giúp. Trân trọng."),
    H2("Mẫu email gửi HR Onboarding"),
    P("Kính gửi HR Onboarding, tôi sắp bắt đầu làm việc vào [ngày đầu tiên] và chưa nhận được [thư cần thiết]. Nhờ HR Onboarding xác nhận giúp tôi. Trân trọng."),
    H2("Mẫu báo sự cố tới Trực SOC"),
    P("Kính gửi Trực SOC, tôi phát hiện [mô tả ngắn, ví dụ: máy có dấu hiệu nhiễm mã độc] vào [thời điểm]. Tôi đã ngắt kết nối mạng của thiết bị và chưa xóa bất kỳ dữ liệu nào. Nhờ Trực SOC hướng dẫn xử lý tiếp. Trân trọng."),

    H1("Câu hỏi thường gặp"),
    P("Hỏi: Email của HR Onboarding là gì? Đáp: hr-onboarding@vsf-demo.example, hoặc dùng HR Portal."),
    P("Hỏi: Email của IT Helpdesk là gì? Đáp: it-helpdesk@vsf-demo.example, hoặc dùng cổng IT."),
    P("Hỏi: Tôi báo sự cố bảo mật cho ai? Đáp: Trực SOC qua soc-oncall@vsf-demo.example, hoạt động 24/7."),
    P("Hỏi: Tôi gửi yêu cầu cho VinSOC trực tiếp được không? Đáp: Không, yêu cầu VinSOC đi qua IT Helpdesk."),
    P("Hỏi: Facilities hỗ trợ những việc gì? Đáp: Chỗ ngồi, thẻ từ và thẻ xe, qua facilities@vsf-demo.example hoặc cổng Facilities."),
    P("Hỏi: Quầy tiếp nhận ở đâu? Đáp: Hà Nội: tầng 1 tòa TechnoPark. TP. Hồ Chí Minh: tầng trệt Vincom Center Đồng Khởi."),
    P("Hỏi: Giờ hỗ trợ của IT Helpdesk? Đáp: 8:00 - 18:00."),
    P("Hỏi: Giờ hỗ trợ của HR Onboarding và Facilities? Đáp: 8:30 - 17:30."),
    P("Hỏi: Danh bạ có số điện thoại hay tên cá nhân không? Đáp: Không, danh bạ chỉ nêu đầu mối theo đội."),
    P("Hỏi: Đầu mối không phản hồi thì sao? Đáp: Nhắc lại một lần, sau đó thông báo cho quản lý trực tiếp để leo thang."),

    H1("Lịch sử sửa đổi"),
    T(["Phiên bản", "Ngày", "Nội dung thay đổi"], [
        ["1.0", "2025-03-01", "Ban hành danh bạ đầu mối theo đội."],
        ["1.5", "2025-11-01", "Bổ sung đầu mối Trực SOC và nguyên tắc liên hệ VinSOC qua IT Helpdesk."],
        ["2.0", "2026-08-01", "Bổ sung hướng dẫn khi nào liên hệ ai, quy tắc leo thang và các mẫu email; chuẩn hóa kênh liên hệ."],
    ], widths=[2.4, 3, 7.6]),
]


# =====================================================================================================================
# P10 Hướng dẫn nhận thẻ từ và đăng ký thẻ xe
# =====================================================================================================================
_P10 = [
    H1("Thông tin kiểm soát tài liệu"),
    T(["Hạng mục", "Nội dung"], [
        ["Mã tài liệu", "SYN-P10"],
        ["Tên tài liệu", "Hướng dẫn nhận thẻ từ và đăng ký thẻ xe"],
        ["Phiên bản", "1.0"],
        ["Đơn vị sở hữu", _FAC],
        ["Người phê duyệt", "Trưởng ban Hành chính - Cơ sở vật chất"],
        ["Đối tượng áp dụng", "Nhân sự mới và nhân sự đang làm việc tại các văn phòng"],
        ["Phân loại", "Nội bộ"],
        ["Ghi chú", _NOTE],
    ], widths=[4, 9]),

    H1("Mục đích, phạm vi và đối tượng"),
    P("Tài liệu hướng dẫn cách nhân sự mới nhận thẻ từ để ra vào tòa nhà trong ngày đầu tiên và cách đăng ký thẻ xe khi có nhu cầu gửi xe tại tòa nhà. Mục tiêu là nhân sự có thể vào khu vực làm việc ngay từ ngày đầu "
      "và biết đường đăng ký thẻ xe đúng biểu mẫu, đúng kênh, tránh phải hỏi nhiều nơi."),
    P("Phạm vi gồm việc nhận thẻ từ tại Quầy tiếp nhận, đăng ký thẻ xe bằng form FAC-02, cách xử lý khi thẻ bị mất hoặc hỏng ở mức nguyên tắc chung, và các quy tắc sử dụng thẻ. "
      "Tài liệu không quy định mức phí hay chi tiết nhà thầu bãi xe. Những nội dung đó do Ban Hành chính hướng dẫn riêng khi cần."),
    H2("Tài liệu liên quan"),
    B("Hướng dẫn ngày đầu đi làm: mốc nhận thẻ từ trong lịch ngày đầu tiên.",
      "Quy trình nhận chỗ ngồi và đổi chỗ ngồi: quản lý chỗ ngồi cũng do Facilities phụ trách.",
      "Danh bạ đầu mối theo đội: kênh liên hệ Facilities và Quầy tiếp nhận.",
      "Lịch tuần đầu tiên của nhân sự mới: các hoạt động của tuần đầu, trong đó cần mang thẻ từ mỗi ngày."),

    H1("Định nghĩa và thuật ngữ"),
    T(["Thuật ngữ", "Ý nghĩa"], [
        ["Thẻ từ", "Thẻ ra vào tòa nhà và khu vực làm việc, đồng thời là thẻ nhân viên."],
        ["Thẻ xe", "Thẻ dùng để gửi và lấy xe tại bãi xe của tòa nhà."],
        ["Quầy tiếp nhận", "Điểm đón nhân sự mới và phát thẻ từ tại từng văn phòng."],
        ["FAC-02", "Form đăng ký thẻ xe trên cổng Facilities."],
        ["Cổng Facilities", "Cổng yêu cầu của Facilities, gồm các form FAC-01 và FAC-02."],
        ["Ban Hành chính", "Đơn vị xử lý hàng đợi yêu cầu thẻ xe và các yêu cầu Facilities khác."],
        ["Hàng đợi", "Danh sách yêu cầu đang chờ xử lý theo thứ tự gửi."],
        ["Loại xe", "Xe máy hoặc ô tô, chọn khi điền FAC-02."],
    ], widths=[3.4, 9.6]),

    H1("Vai trò và trách nhiệm"),
    T(["Vai trò", "Trách nhiệm"], [
        ["Quầy tiếp nhận", "Phát thẻ từ cho nhân sự mới cùng thủ tục tiếp nhận, hướng dẫn cách sử dụng thẻ."],
        ["HR Onboarding", "Cung cấp thông tin nhân sự mới cho Quầy tiếp nhận để chuẩn bị thẻ."],
        ["Facilities (Ban Hành chính)", "Quản lý thẻ từ, xử lý form FAC-02 trong 3 ngày làm việc."],
        ["Quản lý trực tiếp", "Hỗ trợ xác nhận thông tin khi có sự cố thẻ."],
        ["Nhân sự mới", "Nhận thẻ, giữ gìn thẻ, đăng ký thẻ xe đúng quy định và báo ngay khi mất hoặc hỏng thẻ."],
    ], widths=[3.8, 9.2]),

    H1("Quy trình chi tiết"),
    H2("Nhận thẻ từ"),
    P("Thẻ từ được nhận tại Quầy tiếp nhận vào ngày đầu tiên cùng với thủ tục tiếp nhận. Giờ có mặt và địa điểm Quầy tiếp nhận ở từng văn phòng được nêu trong Hướng dẫn ngày đầu đi làm."),
    N("Đến Quầy tiếp nhận của văn phòng mình và báo họ tên, bộ phận.",
      "Xuất trình Căn cước công dân bản gốc để đối chiếu thông tin.",
      "Nhận thẻ từ do nhân viên tiếp nhận phát và kiểm tra thẻ.",
      "Ký nhận thẻ theo hướng dẫn của Quầy tiếp nhận.",
      "Nghe hướng dẫn về khu vực được phép ra vào và cách quẹt thẻ.",
      "Đeo thẻ khi ở trong tòa nhà theo Nội quy lao động."),
    T(["Mốc", "Việc phải làm", "Đơn vị"], [
        ["Trước ngày đầu tiên", "Chuẩn bị thẻ cho nhân sự mới dựa trên thông tin từ HR Onboarding", "Quầy tiếp nhận và Facilities"],
        ["Ngày đầu tiên", "Phát thẻ từ cùng thủ tục tiếp nhận", "Quầy tiếp nhận"],
        ["Ngay sau khi nhận", "Kiểm tra thẻ, thử quẹt thẻ tại cửa", "Nhân sự mới"],
        ["Khi có sự cố", "Báo Facilities", "Nhân sự mới"],
    ], widths=[3.4, 6.6, 3]),

    H2("Đăng ký thẻ xe"),
    P("Nhân sự cần gửi xe đăng ký thẻ xe bằng form FAC-02 trên cổng Facilities. Yêu cầu được chuyển vào hàng đợi của Ban Hành chính và xử lý trong 3 ngày làm việc. "
      "Nhân sự không cần có thẻ xe trong ngày đầu tiên và có thể gửi form sau khi đã nhận thẻ từ và có mã nhân viên."),
    N("Chuẩn bị mã nhân viên, loại xe và biển số xe.",
      "Mở cổng Facilities tại https://facilities.vsf-demo.example/requests và chọn form FAC-02.",
      "Điền mã nhân viên, chọn loại xe là Xe máy hoặc Ô tô, nhập biển số xe chính xác.",
      "Kiểm tra lại thông tin rồi gửi yêu cầu.",
      "Yêu cầu vào hàng đợi của Ban Hành chính.",
      "Chờ xử lý trong 3 ngày làm việc và nhận thẻ xe theo hướng dẫn của Facilities."),
    T(["Trường của FAC-02", "Bắt buộc", "Cách điền"], [
        ["Mã nhân viên", "Có", "Mã được cấp khi vào làm"],
        ["Loại xe", "Có", "Chọn Xe máy hoặc Ô tô"],
        ["Biển số xe", "Có", "Ghi đúng biển số như trên giấy tờ xe"],
    ], widths=[3.6, 2.4, 7]),

    H2("Quy tắc sử dụng thẻ từ và thẻ xe"),
    B("Thẻ từ và thẻ xe là của cá nhân, không cho người khác mượn hoặc dùng chung.",
      "Đeo thẻ nhân viên khi ở trong tòa nhà theo Nội quy lao động.",
      "Không tự ý sao chép, chỉnh sửa hoặc dán thêm vật che lên thẻ.",
      "Thẻ xe chỉ dùng cho loại xe và biển số đã đăng ký trong FAC-02.",
      "Khi đổi xe hoặc đổi biển số, gửi yêu cầu mới trên cổng Facilities thay vì dùng thẻ cho xe khác.",
      "Tuân thủ hướng dẫn của bảo vệ và biển báo tại bãi xe."),

    H2("Thẻ bị mất hoặc hỏng"),
    P("Tài liệu này chỉ nêu nguyên tắc chung, không quy định mức phí. Nếu có chi phí làm lại thẻ, Ban Hành chính sẽ thông báo theo quy định hiện hành của công ty."),
    N("Báo ngay cho Facilities qua email facilities@vsf-demo.example hoặc cổng Facilities khi phát hiện mất hoặc hỏng thẻ.",
      "Nêu họ tên, bộ phận, loại thẻ (thẻ từ hoặc thẻ xe) và tình huống xảy ra.",
      "Nếu mất thẻ từ, nhân sự nên báo càng sớm càng tốt để tránh người khác dùng thẻ vào tòa nhà.",
      "Facilities hướng dẫn cách nhận thẻ thay thế và cách xử lý thẻ cũ.",
      "Nếu việc mất thẻ liên quan đến mất thiết bị hoặc nghi ngờ lộ tài khoản, đồng thời báo Trực SOC theo Quy trình báo cáo sự cố bảo mật."),

    H2("Cam kết thời gian"),
    T(["Hạng mục", "Thời hạn", "Đơn vị"], [
        ["Nhận thẻ từ", "Ngày đầu tiên, tại Quầy tiếp nhận", "Quầy tiếp nhận"],
        ["Xử lý form FAC-02 (thẻ xe)", "3 ngày làm việc", "Facilities (Ban Hành chính)"],
        ["Thẻ từ bị mất hoặc hỏng", "Báo ngay khi phát hiện", "Nhân sự mới, Facilities"],
    ], widths=[5, 5, 3]),

    H1("Trường hợp đặc biệt và ngoại lệ"),
    T(["Tình huống", "Nguyên nhân", "Cách xử lý"], [
        ["Chưa nhận được thẻ từ trong ngày đầu", "Thẻ chưa sẵn sàng hoặc thông tin chưa đủ", "Báo Quầy tiếp nhận và HR Onboarding để được hỗ trợ vào khu vực làm việc"],
        ["Thẻ từ không mở được cửa", "Thẻ chưa kích hoạt hoặc quyền chưa được thiết lập", "Quay lại Quầy tiếp nhận hoặc báo Facilities"],
        ["Quên thẻ từ ở nhà", "Nhân sự để quên", "Báo Quầy tiếp nhận để được hướng dẫn tạm thời"],
        ["Có cả xe máy và ô tô", "Nhu cầu gửi cả hai loại", "Gửi form FAC-02 cho từng loại xe"],
        ["Nhập sai biển số xe", "Nhập nhầm", "Gửi lại yêu cầu mới với biển số đúng và báo Facilities"],
        ["Yêu cầu FAC-02 chưa có phản hồi", "Đang trong hàng đợi", "Chờ đủ 3 ngày làm việc rồi liên hệ Facilities"],
        ["Chưa có mã nhân viên", "Chưa được cấp", "Liên hệ HR Onboarding trước khi gửi FAC-02"],
    ], widths=[4, 3.8, 5.2]),

    H2("Lỗi thường gặp và cách xử lý"),
    B("Điền FAC-02 nhưng không chọn đúng loại xe: kiểm tra lại và gửi yêu cầu mới.",
      "Đợi đến khi cần gửi xe mới đăng ký: nên đăng ký sớm vì yêu cầu cần 3 ngày làm việc để xử lý.",
      "Nhờ đồng nghiệp đăng ký hộ bằng mã nhân viên của người khác: không được phép, mỗi người tự đăng ký cho mình.",
      "Nhầm cổng: yêu cầu thẻ xe gửi qua cổng Facilities, không gửi qua cổng IT."),

    H1("Checklist và mẫu thông báo"),
    H2("Checklist thẻ từ"),
    B("Mang Căn cước công dân bản gốc vào ngày đầu tiên.",
      "Nhận thẻ từ tại Quầy tiếp nhận và kiểm tra.",
      "Thử quẹt thẻ tại cửa được hướng dẫn.",
      "Đeo thẻ khi ở trong tòa nhà."),
    H2("Checklist thẻ xe"),
    B("Có mã nhân viên.",
      "Biết loại xe và biển số.",
      "Đã gửi FAC-02 trên cổng Facilities.",
      "Đã ghi nhận thời hạn xử lý 3 ngày làm việc."),
    H2("Mẫu email báo mất thẻ từ"),
    P("Kính gửi Facilities, tôi là nhân sự bộ phận [tên bộ phận]. Tôi phát hiện mất thẻ từ vào [thời điểm]. Nhờ Facilities hướng dẫn xử lý và cấp thẻ thay thế. Trân trọng."),
    H2("Mẫu email hỏi tiến độ thẻ xe"),
    P("Kính gửi Facilities, tôi đã gửi form FAC-02 vào [ngày gửi] và chưa nhận được thông tin. Nhờ Facilities cho biết tiến độ xử lý. Trân trọng."),

    H1("Câu hỏi thường gặp"),
    P("Hỏi: Tôi nhận thẻ từ ở đâu và khi nào? Đáp: Tại Quầy tiếp nhận vào ngày đầu tiên, cùng với thủ tục tiếp nhận."),
    P("Hỏi: Tôi đăng ký thẻ xe bằng cách nào? Đáp: Dùng form FAC-02 trên cổng Facilities."),
    P("Hỏi: Đăng ký thẻ xe mất bao lâu? Đáp: Yêu cầu vào hàng đợi của Ban Hành chính và được xử lý trong 3 ngày làm việc."),
    P("Hỏi: Loại xe nào có thể đăng ký? Đáp: Xe máy hoặc ô tô, chọn trong form FAC-02."),
    P("Hỏi: Tôi có cần thẻ xe trong ngày đầu tiên không? Đáp: Không bắt buộc, có thể gửi FAC-02 sau khi nhận thẻ từ."),
    P("Hỏi: Tôi mất thẻ từ thì làm gì? Đáp: Báo ngay cho Facilities để được hướng dẫn cấp thẻ thay thế."),
    P("Hỏi: Chi phí làm lại thẻ là bao nhiêu? Đáp: Tài liệu này không nêu mức phí; Ban Hành chính sẽ thông báo theo quy định hiện hành."),
    P("Hỏi: Tôi có thể cho đồng nghiệp mượn thẻ từ không? Đáp: Không, thẻ là của cá nhân."),
    P("Hỏi: Tôi có hai xe thì đăng ký thế nào? Đáp: Gửi một form FAC-02 cho mỗi xe."),
    P("Hỏi: Liên hệ ai khi FAC-02 chưa có phản hồi? Đáp: Facilities qua facilities@vsf-demo.example hoặc cổng Facilities."),

    H1("Lịch sử sửa đổi"),
    T(["Phiên bản", "Ngày", "Nội dung thay đổi"], [
        ["1.0", "2025-09-01", "Ban hành hướng dẫn nhận thẻ từ và đăng ký thẻ xe, kèm quy tắc sử dụng, xử lý mất hoặc hỏng thẻ và câu hỏi thường gặp."],
    ], widths=[2.4, 3, 7.6]),
]


# =====================================================================================================================
BLOCKS = {
    "P01": _P01,
    "P01b": _P01B,
    "P02": _P02,
    "P03": _P03,
    "P04": _P04,
    "P05": _P05,
    "P10": _P10,
}

STYLE: dict = {}

QA = [
    # ---- P01 (phiên bản 3.2)
    {"id": "L-P01-1", "q": "Theo hướng dẫn ngày đầu phiên bản 3.2, nếu tôi đến muộn so với giờ có mặt thì phải làm gì?",
     "must_include": ["Báo ngay HR Onboarding và quản lý trực tiếp"], "docs": ["P01"], "as_of": "2026-09-20"},
    {"id": "L-P01-2", "q": "Nếu ngày đầu tôi quên Căn cước công dân bản gốc thì có hoàn tất thủ tục được không?",
     "must_include": ["không thể hoàn tất thủ tục cho tới khi xuất trình bản gốc"], "docs": ["P01"], "as_of": "2026-09-20"},
    {"id": "L-P01-3", "q": "Sau buổi giới thiệu công ty và an toàn thông tin, tôi nên làm gì để kịp gặp Buddy?",
     "must_include": ["đi thẳng từ Phòng đào tạo tới khu vực làm việc của đội"], "docs": ["P01"], "as_of": "2026-09-20"},
    {"id": "L-P01-4", "q": "Thư giới thiệu đội có danh sách Mentor và Buddy được gửi chậm nhất khi nào so với ngày đầu tiên?",
     "must_include": ["Chậm nhất 2 ngày làm việc trước ngày đầu tiên"], "docs": ["P01"], "as_of": "2026-09-20"},
    {"id": "L-P01-5", "q": "Khi nhận thiết bị tại Bàn IT tôi phải làm những gì và ai chịu trách nhiệm bảo quản?",
     "must_include": ["Ký xác nhận thiết bị", "chịu trách nhiệm bảo quản thiết bị từ thời điểm ký"], "docs": ["P01"], "as_of": "2026-09-20"},

    # ---- P01b (phiên bản 3.3)
    {"id": "L-P01b-1", "q": "Theo hướng dẫn ngày đầu phiên bản 3.3, giữa buổi giới thiệu và buổi gặp Buddy có khoảng nghỉ không?",
     "must_include": ["một khoảng nghỉ ngắn"], "docs": ["P01b"], "as_of": "2026-10-05"},
    {"id": "L-P01b-2", "q": "Phiên bản 3.3 của hướng dẫn ngày đầu đi làm áp dụng cho những nhân sự nào?",
     "must_include": ["áp dụng cho nhân sự bắt đầu làm việc từ ngày đó"], "docs": ["P01b"], "as_of": "2026-10-05"},
    {"id": "L-P01b-3", "q": "Ở mốc tiếp nhận và nhận thẻ từ, tôi phải xuất trình giấy tờ nào để đối chiếu?",
     "must_include": ["Xuất trình Căn cước công dân bản gốc để đối chiếu với hồ sơ"], "docs": ["P01b"], "as_of": "2026-10-05"},
    {"id": "L-P01b-4", "q": "Nếu tôi không thể đến vì ốm vào ngày đầu tiên thì báo cho ai?",
     "must_include": ["Báo cho quản lý trực tiếp và HR Onboarding trước giờ có mặt"], "docs": ["P01b"], "as_of": "2026-10-05"},

    # ---- P02
    {"id": "L-P02-1", "q": "Nếu ngày đầu tiên của tôi không rơi vào Thứ Hai thì lịch tuần đầu được xử lý thế nào?",
     "must_include": ["lịch dời tương ứng"], "docs": ["P02"]},
    {"id": "L-P02-2", "q": "Nếu tôi vắng buổi đào tạo an toàn thông tin của VinSOC thì sao?",
     "must_include": ["sắp xếp buổi bù"], "docs": ["P02"]},
    {"id": "L-P02-3", "q": "Trong tuần đầu tôi có phải làm ra sản phẩm công việc chính thức không?",
     "must_include": ["Không cần tạo ra sản phẩm công việc chính thức trong tuần đầu"], "docs": ["P02"]},
    {"id": "L-P02-4", "q": "Giờ cụ thể của các buổi từ Thứ Ba đến Thứ Sáu trong tuần đầu được thông báo qua đâu?",
     "must_include": ["lời mời lịch"], "docs": ["P02"]},

    # ---- P03
    {"id": "L-P03-1", "q": "Nếu Mentor hoặc Buddy không thể tiếp tục vì nghỉ dài ngày hay chuyển đội thì ai xử lý?",
     "must_include": ["báo ngay cho HR Onboarding"], "docs": ["P03"]},
    {"id": "L-P03-2", "q": "Mentor và Buddy có quyền phê duyệt nghỉ phép cho nhân sự mới không?",
     "must_include": ["không có quyền phê duyệt nghỉ phép"], "docs": ["P03"]},
    {"id": "L-P03-3", "q": "Quản lý trực tiếp có vai trò gì trong việc phân công Mentor và Buddy?",
     "must_include": ["chỉ xác nhận thông tin phân công"], "docs": ["P03"]},
    {"id": "L-P03-4", "q": "Một Buddy có nên được giao cho nhiều nhân sự mới cùng lúc không?",
     "must_include": ["quá nhiều nhân sự mới cùng lúc"], "docs": ["P03"]},

    # ---- P04
    {"id": "L-P04-1", "q": "Trong form FAC-01 trường nào không bắt buộc điền?",
     "must_include": ["Vị trí hiện tại (không bắt buộc)"], "docs": ["P04"]},
    {"id": "L-P04-2", "q": "Nếu vị trí ghi trong Thư tiếp nhận đã có người ngồi thì tôi xử lý thế nào?",
     "must_include": ["Không tự chuyển bàn"], "docs": ["P04"]},
    {"id": "L-P04-3", "q": "Trong lúc chờ Facilities xử lý yêu cầu đổi chỗ ngồi, tôi ngồi ở đâu?",
     "must_include": ["tiếp tục ngồi tại vị trí hiện tại"], "docs": ["P04"]},
    {"id": "L-P04-4", "q": "Nếu quá 3 ngày làm việc mà yêu cầu FAC-01 chưa có phản hồi thì tôi làm gì?",
     "must_include": ["liên hệ facilities@vsf-demo.example"], "docs": ["P04"]},

    # ---- P05
    {"id": "L-P05-1", "q": "VinSOC có nhận yêu cầu trực tiếp không, và sự cố bảo mật khẩn cấp thì báo ở đâu?",
     "must_include": ["không đi qua IT Helpdesk mà báo trực tiếp cho Trực SOC"], "docs": ["P05"]},
    {"id": "L-P05-2", "q": "Nếu đầu mối chưa phản hồi thì quy tắc leo thang gồm những bước nào?",
     "must_include": ["gửi nhắc lại một lần", "thông báo cho quản lý trực tiếp"], "docs": ["P05"]},
    {"id": "L-P05-3", "q": "Tôi quên mật khẩu thì có gửi cho Trực SOC được không?",
     "must_include": ["không gửi cho Trực SOC mà gửi cho IT Helpdesk"], "docs": ["P05"]},
    {"id": "L-P05-4", "q": "Khi liên hệ đầu mối tôi có nên gửi mật khẩu để họ kiểm tra giúp không?",
     "must_include": ["Không gửi mật khẩu, mã xác thực hoặc dữ liệu nhạy cảm qua email hay chat"], "docs": ["P05"]},

    # ---- P10
    {"id": "L-P10-1", "q": "Tôi nhập sai biển số xe trong form FAC-02 thì xử lý thế nào?",
     "must_include": ["Gửi lại yêu cầu mới với biển số đúng"], "docs": ["P10"]},
    {"id": "L-P10-2", "q": "Nếu mất thẻ từ kèm mất thiết bị hoặc nghi lộ tài khoản thì phải báo thêm cho ai?",
     "must_include": ["đồng thời báo Trực SOC"], "docs": ["P10"]},
    {"id": "L-P10-3", "q": "Tôi có thể cho đồng nghiệp mượn thẻ từ hoặc thẻ xe không?",
     "must_include": ["không cho người khác mượn hoặc dùng chung"], "docs": ["P10"]},
    {"id": "L-P10-4", "q": "Tôi có cần có thẻ xe ngay trong ngày đầu tiên không?",
     "must_include": ["không cần có thẻ xe trong ngày đầu tiên"], "docs": ["P10"]},
    {"id": "L-P10-5", "q": "Tài liệu về thẻ từ và thẻ xe có nêu mức phí làm lại thẻ không?",
     "must_include": ["không quy định mức phí"], "docs": ["P10"]},
]
