"""Tài liệu chính sách dài, nhóm A: D01, D02, D03a, D03b, D03c, D04.

Mọi dữ kiện trong các tài liệu này là GIẢ ĐỊNH để mô phỏng và kiểm thử chatbot; không phải chính sách VSF đã xác nhận.
"""
from __future__ import annotations

from blocks import H1, H2, P, B, N, T, PB  # noqa: F401

NOTE = "Tài liệu giả lập để kiểm thử, không phải chính sách VSF đã xác nhận"
HR_OWNER = "Phòng Nhân sự (giả định)"


def ctrl(code, approver, audience, status, extra=(), owner=HR_OWNER, review="Hằng năm"):
    """Bảng thông tin kiểm soát tài liệu (2 cột)."""
    rows = [
        ["Mã tài liệu", code],
        ["Đơn vị sở hữu", owner],
        ["Người phê duyệt", approver],
        ["Đối tượng áp dụng", audience],
        ["Phân loại", "Nội bộ"],
        ["Trạng thái hiệu lực", status],
        ["Chu kỳ rà soát", review],
    ]
    rows += [list(x) for x in extra]
    rows.append(["Ghi chú", NOTE])
    return T(["Mục", "Nội dung"], rows, widths=[3, 9])


# =====================================================================================================
# D01 - Nội quy lao động
# =====================================================================================================
D01 = [
    H1("Thông tin kiểm soát tài liệu"),
    ctrl("SYN-D01", "Giám đốc Nhân sự", "Toàn bộ nhân sự làm việc tại công ty", "Đang hiệu lực"),
    P("Bảng trên giúp người đọc nhận diện đúng tài liệu và biết đơn vị chịu trách nhiệm nội dung. Bản in hoặc bản sao lưu ngoài kho tài liệu nội bộ không còn được kiểm soát; khi cần đối chiếu, nhân sự luôn dùng phiên bản đang hiển thị trên kho tài liệu nội bộ. Mọi thay đổi nội dung chỉ có hiệu lực sau khi được người phê duyệt ký ban hành và được ghi vào phần Lịch sử sửa đổi ở cuối tài liệu."),

    H1("Mục đích và phạm vi"),
    H2("Mục đích"),
    P("Nội quy lao động này quy định các nguyên tắc chung về thời giờ làm việc, hình ảnh, nghỉ phép, bảo mật thông tin, ứng xử và xử lý vi phạm tại công ty. Mục tiêu là giúp mọi nhân sự hiểu rõ điều mình được làm, điều mình phải làm và cách xử lý khi có tình huống ngoài dự kiến, để môi trường làm việc công bằng, minh bạch và an toàn cho tất cả mọi người."),
    P("Nội quy chỉ nêu nguyên tắc và mức yêu cầu tối thiểu. Các chính sách chuyên đề như nghỉ phép, thử việc, làm việc từ xa hoặc bảo mật dữ liệu có văn bản riêng, quy định chi tiết hơn và được nhắc tên trong từng mục bên dưới."),
    H2("Phạm vi áp dụng"),
    P("Nội quy này áp dụng cho toàn bộ nhân sự làm việc tại công ty, gồm nhân viên chính thức, nhân viên thử việc và thực tập sinh."),
    P("Nội quy được áp dụng tại mọi văn phòng của công ty và cả khi nhân sự làm việc từ xa, làm việc ngoài văn phòng hoặc tham dự sự kiện do công ty tổ chức. Nhân sự của nhà thầu hoặc đối tác làm việc trong tòa nhà không thuộc đối tượng của nội quy này nhưng phải tuân thủ các yêu cầu về an ninh, đeo thẻ và bảo mật thông tin nêu trong hợp đồng dịch vụ với công ty."),
    H2("Căn cứ và tài liệu liên quan"),
    P("Nội quy được xây dựng dựa trên Bộ luật Lao động hiện hành và các văn bản hướng dẫn thi hành. Khi quy định của nội quy trái với quy định bắt buộc của pháp luật, quy định của pháp luật được áp dụng. Người đọc cần tham khảo thêm các tài liệu sau:"),
    B("Nội quy trang phục: yêu cầu về trang phục và hình ảnh tại văn phòng.",
      "Chính sách nghỉ phép năm: số ngày phép, cách đăng ký, điều kiện chuyển phép (dùng phiên bản đang có hiệu lực tại ngày nghỉ).",
      "Chính sách thử việc: thời gian, lương, quyền lợi và đánh giá thử việc.",
      "Chính sách làm việc từ xa: điều kiện làm việc từ xa ngoài thứ Bảy.",
      "Chính sách phân loại dữ liệu: bốn cấp độ phân loại và quy tắc xử lý từng cấp.",
      "Chính sách mật khẩu và xác thực: yêu cầu mật khẩu và xác thực nhiều yếu tố.",
      "Quy trình báo cáo sự cố bảo mật: các bước báo cáo khi có sự cố.",
      "Sổ tay nhân viên: tổng quan công ty, cơ cấu và kênh hỗ trợ.",
      "Danh bạ đầu mối theo đội: đầu mối liên hệ theo từng loại nhu cầu."),
    H2("Nguyên tắc áp dụng"),
    P("Nhân sự có trách nhiệm đọc, hiểu và tuân thủ nội quy ngay từ ngày đầu làm việc. Việc chưa đọc nội quy không phải là lý do để miễn trách nhiệm khi vi phạm. Khi có điều chưa rõ, nhân sự hỏi quản lý trực tiếp hoặc liên hệ HR Onboarding trước khi hành động, thay vì tự suy diễn."),
    P("Khi nội quy và một chính sách chuyên đề cùng điều chỉnh một nội dung, chính sách chuyên đề đang có hiệu lực được ưu tiên áp dụng đối với phần chi tiết. Nội quy vẫn là căn cứ để xác định hành vi có phải là vi phạm hay không và mức độ xử lý."),

    H1("Định nghĩa và thuật ngữ"),
    T(["Thuật ngữ", "Định nghĩa dùng trong nội quy này"], [
        ["Nhân sự", "Mọi người làm việc cho công ty theo hợp đồng lao động, hợp đồng thử việc hoặc thỏa thuận thực tập."],
        ["Nhân viên chính thức", "Nhân sự đã hoàn thành thử việc và ký hợp đồng lao động chính thức."],
        ["Nhân viên thử việc", "Nhân sự đang trong thời gian thử việc theo Chính sách thử việc."],
        ["Thực tập sinh", "Người làm việc theo chương trình thực tập, không thuộc diện nhân viên chính thức."],
        ["Quản lý trực tiếp", "Người được phân công quản lý công việc hằng ngày của nhân sự, là đầu mối đầu tiên cho các đề nghị về giờ giấc và nghỉ phép."],
        ["Trưởng phòng", "Người đứng đầu đơn vị mà nhân sự trực thuộc, phê duyệt các đề nghị vượt thẩm quyền của quản lý trực tiếp."],
        ["Khung giờ vào làm", "Khoảng thời gian từ 8:00 đến 9:30 mỗi ngày làm việc, trong đó nhân sự được chọn giờ bắt đầu ngày làm việc."],
        ["Ngày làm việc", "Các ngày từ thứ Hai đến thứ Sáu, không kể ngày nghỉ lễ theo lịch công ty công bố. Thứ Bảy làm việc từ xa theo phân công không dùng để tính thời hạn xử lý hồ sơ, trừ khi văn bản có quy định khác."],
        ["Làm việc từ xa", "Làm việc ngoài văn phòng, kết nối với hệ thống nội bộ theo hướng dẫn của Khối Công nghệ thông tin (giả định)."],
        ["HR Portal", "Cổng thông tin nhân sự nội bộ, nơi ghi nhận giờ giấc bất thường, đăng ký nghỉ phép và theo dõi kết quả xử lý."],
        ["Thông tin Nội bộ", "Thông tin thuộc cấp độ Nội bộ theo Chính sách phân loại dữ liệu, không được chia sẻ ra ngoài công ty."],
        ["Vi phạm", "Hành vi không tuân thủ nội quy, được phân thành ba mức: nhẹ, trung bình và nghiêm trọng."],
    ], widths=[3, 9]),

    H1("Vai trò và trách nhiệm"),
    P("Bảng dưới đây mô tả bằng lời ai làm gì khi thực hiện nội quy. Một việc có thể có nhiều vai trò cùng tham gia, nhưng chỉ có một vai trò chịu trách nhiệm chính."),
    T(["Vai trò", "Trách nhiệm chính", "Ghi chú"], [
        ["Nhân sự", "Tuân thủ nội quy, báo giờ giấc bất thường đúng hạn, giữ gìn tài sản và thông tin của công ty.", "Chịu trách nhiệm chính về hành vi của mình."],
        ["Quản lý trực tiếp", "Phổ biến nội quy cho nhân sự mới, theo dõi giờ giấc, phê duyệt đề nghị thuộc thẩm quyền, nhắc nhở lần đầu.", "Không tự ý xử lý mức trung bình trở lên."],
        ["Trưởng phòng", "Phê duyệt đề nghị vượt thẩm quyền, xem xét đề xuất khiển trách, tham gia xử lý khiếu nại.", "Phối hợp với Phòng Nhân sự."],
        ["Phòng Nhân sự", "Sở hữu nội quy, hướng dẫn áp dụng, lưu hồ sơ vi phạm, tổ chức xử lý và giải quyết khiếu nại.", "Là đơn vị chịu trách nhiệm chính về nội dung tài liệu."],
        ["Ban Hành chính - Cơ sở vật chất (giả định)", "Quản lý thẻ nhân viên, kiểm soát ra vào tòa nhà, an toàn phòng cháy chữa cháy.", "Liên hệ qua Facilities."],
        ["Khối Công nghệ thông tin (giả định)", "Cấp tài khoản, thiết bị và hướng dẫn kết nối từ xa.", "Liên hệ qua IT Helpdesk."],
        ["Trung tâm An ninh mạng VinSOC (giả định)", "Tiếp nhận và xử lý sự cố bảo mật, kiểm tra phần mềm.", "Sự cố khẩn báo Trực SOC."],
    ], widths=[3.2, 6.3, 3.5]),

    H1("Thời giờ làm việc"),
    H2("Số giờ làm việc và giờ nghỉ trưa"),
    P("Mỗi ngày làm việc 8 giờ, không tính giờ nghỉ trưa. Giờ vào làm linh hoạt trong khung từ 8:00 đến 9:30, giờ ra tương ứng để đủ 8 giờ. Nghỉ trưa 1 giờ. Thứ Bảy làm việc từ xa theo phân công của quản lý."),
    P("Như vậy, một ngày làm việc trọn vẹn gồm 8 giờ làm việc cộng 1 giờ nghỉ trưa, tổng cộng 9 giờ kể từ lúc nhân sự bắt đầu ngày làm việc. Thời điểm nghỉ trưa do nhân sự thống nhất với đội để không ảnh hưởng đến các cuộc họp và lịch hỗ trợ đã được lên trước; nội quy không quy định giờ nghỉ trưa cố định."),
    H2("Khung giờ vào làm linh hoạt"),
    P("Nhân sự tự chọn giờ bắt đầu trong khung từ 8:00 đến 9:30. Giờ ra được tính bằng giờ vào cộng 8 giờ làm việc và 1 giờ nghỉ trưa. Bảng sau minh họa bốn cách chọn giờ phổ biến:"),
    T(["Giờ vào chọn", "Giờ ra tối thiểu", "Ghi chú"], [
        ["8:00", "17:00", "Đầu khung giờ vào làm"],
        ["8:30", "17:30", "Đã gồm 1 giờ nghỉ trưa"],
        ["9:00", "18:00", "Đã gồm 1 giờ nghỉ trưa"],
        ["9:30", "18:30", "Cuối khung giờ vào làm"],
    ], widths=[3, 3, 6]),
    P("Nhân sự nên giữ giờ vào tương đối ổn định để đồng nghiệp dễ sắp xếp họp. Nếu đội có cuộc họp chung vào đầu ngày, quản lý thông báo trước để mọi người chọn giờ vào phù hợp; đây là thỏa thuận trong đội và không thay đổi khung 8:00 đến 9:30 của nội quy."),
    H2("Vào muộn hoặc rời sớm"),
    P("Trường hợp vào muộn hơn 9:30 hoặc cần rời sớm, nhân sự phải báo cho quản lý trực tiếp trước 9:30 cùng ngày và ghi nhận trên HR Portal."),
    P("Nội dung ghi nhận gồm: ngày phát sinh, giờ vào hoặc giờ ra dự kiến, lý do ngắn gọn và cách bù thời gian nếu có. Quản lý xác nhận trên HR Portal; nếu cần trao đổi thêm, quản lý liên hệ nhân sự ngay trong ngày. Việc ghi nhận không đồng nghĩa với việc được miễn bù giờ; khi thời gian làm việc trong ngày chưa đủ 8 giờ, nhân sự phải bù hoặc xin nghỉ phép theo chính sách nghỉ phép hiện hành."),
    P("Trường hợp đột xuất không thể báo trước 9:30, chẳng hạn cấp cứu hoặc sự cố giao thông nghiêm trọng, nhân sự báo cho quản lý ngay khi có thể bằng bất kỳ kênh nào và hoàn tất ghi nhận trên HR Portal trong ngày làm việc kế tiếp. Nếu lý do được quản lý xác nhận là chính đáng, việc báo muộn không bị coi là vi phạm."),
    H2("Làm việc từ xa vào thứ Bảy"),
    P("Thứ Bảy làm việc từ xa theo phân công của quản lý. Chỉ nhân sự có tên trong phân công của tuần đó mới phải làm việc; quản lý thông báo danh sách và nội dung công việc chậm nhất vào cuối ngày làm việc thứ Năm của tuần đó. Trong ngày làm việc từ xa, nhân sự có mặt trực tuyến trong khung giờ đã thống nhất với quản lý và kết nối VPN khi truy cập hệ thống nội bộ theo Chính sách làm việc từ xa."),
    P("Việc ghi nhận thời gian làm việc thứ Bảy và cách bù nghỉ (nếu có) thực hiện theo hướng dẫn của Phòng Nhân sự, nội quy này không quy định thêm mức bù riêng."),
    H2("Ví dụ minh họa"),
    P("Ví dụ 1. Nhân sự chọn vào lúc 8:30. Ngày làm việc kết thúc tối thiểu lúc 17:30. Nếu buổi sáng nhân sự đến lúc 8:45 thì giờ ra tối thiểu tương ứng là 17:45, vì nhân sự vẫn nằm trong khung giờ vào làm và chỉ cần đủ 8 giờ làm việc."),
    P("Ví dụ 2. Nhân sự có lịch khám bệnh nên dự kiến vào lúc 10:30. Vì giờ này muộn hơn 9:30, nhân sự phải báo cho quản lý trực tiếp trước 9:30 cùng ngày, ghi nhận trên HR Portal và cho biết sẽ bù thời gian vào cuối ngày hoặc xin nghỉ phép theo chính sách nghỉ phép."),
    P("Ví dụ 3. Nhân sự quên báo và đến lúc 10:00 mà không có tin nhắn nào cho quản lý. Trường hợp này không đáp ứng quy định báo trước 9:30. Quản lý ghi nhận và nhắc nhở; nếu lặp lại thì được xử lý theo mục Xử lý vi phạm."),
    P("Ví dụ 4. Nhân sự được phân công làm việc từ xa vào thứ Bảy nhưng sáng thứ Bảy mất kết nối mạng tại nhà. Nhân sự báo ngay cho quản lý, dùng phương án kết nối dự phòng do IT Helpdesk hướng dẫn và ghi nhận sự việc để quản lý xem xét việc sắp xếp lại công việc."),
    H2("Thời hạn và kênh báo giờ giấc"),
    T(["Tình huống", "Thời hạn báo", "Kênh báo", "Người nhận"], [
        ["Vào muộn hơn 9:30", "Trước 9:30 cùng ngày", "Báo trực tiếp và ghi HR Portal", "Quản lý trực tiếp"],
        ["Cần rời sớm", "Trước 9:30 cùng ngày", "Báo trực tiếp và ghi HR Portal", "Quản lý trực tiếp"],
        ["Đột xuất, không kịp báo", "Ngay khi có thể", "Kênh liên lạc bất kỳ", "Quản lý trực tiếp"],
        ["Hoàn tất ghi nhận sau sự việc đột xuất", "Trong ngày làm việc kế tiếp", "HR Portal", "Quản lý trực tiếp"],
        ["Không thể làm việc từ xa thứ Bảy", "Ngay khi phát hiện", "Báo trực tiếp", "Quản lý trực tiếp"],
    ], widths=[4, 3, 3.5, 2.5]),

    H1("Trang phục và hình ảnh"),
    P("Nhân sự thực hiện theo Nội quy trang phục hiện hành. Thẻ nhân viên phải được đeo khi ở trong tòa nhà."),
    P("Thẻ nhân viên được đeo ở vị trí dễ nhìn thấy, không che khuất ảnh và mã thẻ. Thẻ là tài sản của công ty, chỉ dùng cho chính chủ; nghiêm cấm cho mượn, đổi thẻ hoặc dùng thẻ của người khác để ra vào. Khi làm mất thẻ, nhân sự báo ngay cho Ban Hành chính - Cơ sở vật chất qua Facilities để khóa thẻ và cấp lại."),
    P("Khi tham gia họp trực tuyến với đối tác hoặc khách hàng, nhân sự giữ hình ảnh gọn gàng như khi họp trực tiếp. Chi tiết về loại trang phục được phép và không được phép nằm trong Nội quy trang phục."),

    H1("Nghỉ phép và vắng mặt"),
    P("Nhân sự thực hiện việc đăng ký nghỉ phép theo Chính sách nghỉ phép năm hiện hành, thông qua HR Portal."),
    P("Nội quy này chỉ quy định nguyên tắc chung. Số ngày phép, thời hạn đăng ký, cấp phê duyệt và điều kiện chuyển phép do chính sách nghỉ phép năm quy định; nhân sự cần đọc phiên bản có hiệu lực tại ngày dự kiến nghỉ. Nhân viên thử việc thực hiện theo Chính sách thử việc và không áp dụng chế độ phép năm."),
    P("Các trường hợp nghỉ khác như nghỉ ốm, nghỉ việc riêng có lương theo pháp luật hoặc nghỉ không lương được thực hiện theo quy định của pháp luật lao động, chính sách liên quan và hướng dẫn của Phòng Nhân sự. Trong mọi trường hợp, nhân sự phải báo cho quản lý trực tiếp trước khi nghỉ hoặc chậm nhất là trong ngày vắng mặt nếu sự việc đột xuất."),
    P("Vắng mặt không có lý do chính đáng và không báo cho quản lý được coi là vi phạm nội quy. Vắng mặt kéo dài nhiều ngày liên tiếp mà không liên lạc được sẽ được Phòng Nhân sự xem xét theo quy định của Bộ luật Lao động."),

    H1("Bảo mật thông tin và tài sản công ty"),
    H2("Nguyên tắc chia sẻ thông tin"),
    P("Không chia sẻ tài liệu có phân loại Nội bộ trở lên ra bên ngoài công ty. Chi tiết theo Chính sách phân loại dữ liệu."),
    P("Điều này có nghĩa là danh bạ nhân sự, quy trình nội bộ, biên bản họp, dữ liệu lương cá nhân, hợp đồng và dữ liệu khách hàng không được gửi qua email cá nhân, ứng dụng nhắn tin cá nhân, mạng xã hội hoặc lưu trên dịch vụ lưu trữ không do công ty cấp. Chỉ thông tin thuộc cấp Công khai mới được chia sẻ tự do."),
    H2("Tài khoản, thiết bị và phần mềm"),
    B("Mỗi tài khoản công ty chỉ do một người sử dụng; không chia sẻ mật khẩu và thực hiện theo Chính sách mật khẩu và xác thực.",
      "Khóa màn hình khi rời vị trí làm việc, kể cả khi chỉ rời trong thời gian ngắn.",
      "Không tự cài phần mềm ngoài danh mục được duyệt và không tự cài lại hệ điều hành; mọi yêu cầu gửi qua IT Helpdesk.",
      "Không nối thiết bị lưu trữ hoặc thiết bị cá nhân không rõ nguồn gốc vào máy công ty.",
      "Không mở liên kết hoặc tệp cài đặt nhận qua chat hay email nếu chưa được xác minh."),
    H2("Báo cáo sự cố"),
    P("Khi nghi ngờ mã độc, mất thiết bị công ty hoặc tài khoản bị chiếm quyền, nhân sự không tự xử lý, không xóa dấu vết và báo cho Trực SOC theo Quy trình báo cáo sự cố bảo mật. Thời hạn báo là 1 giờ kể từ khi phát hiện. Việc báo cáo trung thực và kịp thời được xem là yếu tố giảm nhẹ khi xem xét trách nhiệm."),
    H2("Giữ gìn tài sản"),
    P("Nhân sự sử dụng thiết bị, thẻ, phòng họp và vật dụng văn phòng đúng mục đích công việc, bảo quản cẩn thận và báo ngay khi hỏng hoặc thất lạc. Khi kết thúc làm việc tại công ty, nhân sự bàn giao đầy đủ thiết bị, thẻ và tài liệu cho quản lý trực tiếp và các đầu mối liên quan."),

    H1("Ứng xử nơi làm việc"),
    P("Nhân sự tôn trọng đồng nghiệp, khách hàng và đối tác; giao tiếp lịch sự, trung thực và tập trung vào công việc. Các hành vi sau đây bị nghiêm cấm trong mọi trường hợp:"),
    B("Quấy rối, đe dọa, xúc phạm hoặc phân biệt đối xử dưới bất kỳ hình thức nào, kể cả trên kênh trực tuyến.",
      "Sử dụng thông tin nội bộ vì mục đích cá nhân hoặc vì lợi ích của bên thứ ba.",
      "Gian lận trong chấm công, báo cáo, chứng từ hoặc hồ sơ nhân sự.",
      "Đến nơi làm việc trong tình trạng bị ảnh hưởng bởi rượu bia hoặc chất cấm; mang vũ khí, chất nguy hiểm vào tòa nhà.",
      "Quay phim, chụp ảnh khu vực làm việc hoặc màn hình có thông tin Nội bộ để đăng tải ra ngoài."),
    P("Xung đột lợi ích phải được khai báo cho quản lý trực tiếp ngay khi phát sinh, ví dụ nhân sự có quan hệ thân thiết với đối tác đang đàm phán với công ty. Quản lý phối hợp với Phòng Nhân sự để quyết định biện pháp phù hợp."),

    H1("An toàn lao động và phòng cháy chữa cháy"),
    P("Nhân sự tuân thủ biển báo, hướng dẫn thoát hiểm và quy định an toàn của tòa nhà, không chặn lối thoát hiểm và không tự ý tháo dỡ thiết bị an toàn. Khi phát hiện nguy cơ mất an toàn, nhân sự báo ngay cho Ban Hành chính - Cơ sở vật chất. Khi có báo động cháy, nhân sự dừng công việc, di chuyển theo lối thoát hiểm và tập trung tại điểm tập kết theo hướng dẫn trong Sổ tay nhân viên."),

    H1("Xử lý vi phạm"),
    H2("Nguyên tắc xử lý"),
    P("Việc xử lý vi phạm dựa trên bốn nguyên tắc: có căn cứ và bằng chứng rõ ràng; tương xứng với tính chất, mức độ và hậu quả của hành vi; bảo đảm quyền giải trình của nhân sự; và tuân thủ trình tự, thời hiệu xử lý kỷ luật theo Bộ luật Lao động. Không ai bị xử lý hai lần cho cùng một hành vi."),
    H2("Các mức xử lý"),
    T(["Mức độ", "Hình thức xử lý", "Ghi chú"], [
        ["Nhẹ", "Nhắc nhở bằng văn bản", "Lần đầu, không gây hậu quả"],
        ["Trung bình", "Khiển trách", "Tái phạm hoặc gây ảnh hưởng đến đồng nghiệp"],
        ["Nghiêm trọng", "Kỷ luật theo Bộ luật Lao động", "Vi phạm bảo mật, gian lận, gây thiệt hại"],
    ], widths=[2, 4, 5]),
    H2("Ví dụ phân loại mức độ"),
    T(["Hành vi", "Mức độ thường gặp", "Lý do"], [
        ["Lần đầu vào muộn hơn 9:30 mà không báo trước", "Nhẹ", "Không gây hậu quả, thiếu quy trình báo"],
        ["Tái phạm không báo giờ giấc sau khi đã bị nhắc nhở bằng văn bản", "Trung bình", "Tái phạm"],
        ["Đăng tài liệu Nội bộ lên mạng xã hội cá nhân", "Nghiêm trọng", "Vi phạm bảo mật"],
        ["Cho người khác mượn thẻ nhân viên để vào tòa nhà", "Trung bình", "Ảnh hưởng an ninh chung, có thể nâng mức nếu gây hậu quả"],
        ["Khai báo sai giờ làm việc để hưởng lợi", "Nghiêm trọng", "Gian lận"],
        ["Có lời nói xúc phạm đồng nghiệp trong cuộc họp", "Trung bình", "Ảnh hưởng đến đồng nghiệp"],
    ], widths=[6, 2.5, 4.5]),
    P("Bảng trên chỉ minh họa cách phân loại. Mức độ cuối cùng do Phòng Nhân sự xác định dựa trên toàn bộ tình tiết, bao gồm ý thức của người vi phạm, việc chủ động khắc phục và hậu quả thực tế."),
    H2("Trình tự xử lý"),
    N("Ghi nhận: quản lý trực tiếp hoặc người phát hiện lập ghi nhận ngắn gọn về hành vi, thời gian và bằng chứng, gửi Phòng Nhân sự.",
      "Xác minh: Phòng Nhân sự xác minh thông tin và xác định mức độ sơ bộ. Với vi phạm mức nhẹ, quản lý trực tiếp có thể nhắc nhở trực tiếp trước khi lập văn bản.",
      "Giải trình: nhân sự được thông báo bằng văn bản về hành vi bị nêu và có 3 ngày làm việc để giải trình. Trong thời gian này nhân sự được quyền cung cấp thêm bằng chứng.",
      "Quyết định: Phòng Nhân sự đề xuất hình thức xử lý; Trưởng phòng cho ý kiến với mức trung bình; mức nghiêm trọng được xử lý theo thủ tục kỷ luật lao động do Phòng Nhân sự chủ trì.",
      "Thông báo và lưu hồ sơ: quyết định được gửi cho nhân sự, quản lý trực tiếp và lưu trong hồ sơ nhân sự theo phân loại Bí mật."),
    H2("Khiếu nại"),
    P("Nhân sự không đồng ý với kết quả xử lý có thể gửi khiếu nại bằng văn bản hoặc email tới hr-onboarding@vsf-demo.example trong 5 ngày làm việc kể từ ngày nhận quyết định, nêu rõ nội dung không đồng ý và bằng chứng kèm theo. Phòng Nhân sự phản hồi trong 5 ngày làm việc kể từ ngày nhận đủ hồ sơ. Việc khiếu nại không làm chậm việc thi hành quyết định trừ khi có thông báo khác. Nhân sự có quyền khiếu nại hoặc khởi kiện theo quy định của pháp luật lao động."),
    P("Công ty không trả đũa nhân sự vì đã báo cáo vi phạm một cách trung thực hoặc tham gia cung cấp thông tin trong quá trình xác minh."),

    H1("Câu hỏi thường gặp"),
    P("Hỏi: Tôi có thể vào làm lúc 9:15 mỗi ngày không? Đáp: Có. Khung giờ vào làm là từ 8:00 đến 9:30, nên 9:15 nằm trong khung. Giờ ra tối thiểu của bạn khi đó là 18:15, đã gồm 8 giờ làm việc và 1 giờ nghỉ trưa."),
    P("Hỏi: Nếu tôi vào lúc 9:45 thì phải làm gì? Đáp: Vì muộn hơn 9:30, bạn phải báo cho quản lý trực tiếp trước 9:30 cùng ngày và ghi nhận trên HR Portal, đồng thời nêu cách bù thời gian."),
    P("Hỏi: Nghỉ trưa có được tính vào 8 giờ làm việc không? Đáp: Không. 8 giờ làm việc không tính giờ nghỉ trưa 1 giờ."),
    P("Hỏi: Thứ Bảy tôi có bắt buộc đi làm không? Đáp: Thứ Bảy làm việc từ xa theo phân công của quản lý. Bạn chỉ phải làm việc khi có tên trong phân công của tuần đó."),
    P("Hỏi: Tôi quên đeo thẻ nhân viên khi vào tòa nhà thì có bị xử lý không? Đáp: Thẻ phải được đeo khi ở trong tòa nhà. Quên đeo thẻ lần đầu thường chỉ bị nhắc nhở; nếu thường xuyên tái phạm thì được xử lý theo mức trung bình."),
    P("Hỏi: Tôi có thể gửi tài liệu nội bộ về email cá nhân để làm việc buổi tối không? Đáp: Không. Tài liệu có phân loại Nội bộ trở lên không được chia sẻ ra ngoài công ty. Hãy dùng VPN và thiết bị công ty theo Chính sách làm việc từ xa."),
    P("Hỏi: Nhân viên thử việc có phải tuân thủ nội quy này không? Đáp: Có. Nội quy áp dụng cho nhân viên chính thức, nhân viên thử việc và thực tập sinh."),
    P("Hỏi: Tôi bị xử lý nhắc nhở bằng văn bản mà thấy chưa đúng thì làm gì? Đáp: Bạn có thể giải trình trong 3 ngày làm việc kể từ khi nhận thông báo, hoặc gửi khiếu nại tới Phòng Nhân sự trong 5 ngày làm việc kể từ ngày nhận quyết định."),
    P("Hỏi: Ai quyết định mức xử lý vi phạm? Đáp: Phòng Nhân sự xác định mức độ dựa trên toàn bộ tình tiết. Quản lý trực tiếp chỉ nhắc nhở lần đầu với vi phạm nhẹ; mức trung bình có ý kiến của Trưởng phòng."),
    P("Hỏi: Tôi phải làm gì nếu nghi ngờ máy có mã độc? Đáp: Không tự xử lý, ngắt kết nối mạng và báo cho Trực SOC trong 1 giờ kể từ khi phát hiện, theo Quy trình báo cáo sự cố bảo mật."),

    H1("Phụ lục"),
    H2("Phụ lục A. Mẫu thông báo vào muộn hoặc rời sớm"),
    P("Gửi quản lý trực tiếp trước 9:30 cùng ngày và ghi lại trên HR Portal. Nội dung mẫu: 'Chào anh chị, hôm nay em dự kiến vào làm lúc [giờ] do [lý do ngắn gọn]. Em sẽ bù thời gian bằng cách [làm thêm cuối ngày hoặc xin nghỉ phép]. Em sẽ cập nhật ngay nếu có thay đổi.'"),
    H2("Phụ lục B. Danh sách kiểm tra cho nhân sự mới"),
    B("Đã đọc Nội quy lao động và Nội quy trang phục.",
      "Đã nhận thẻ nhân viên và hiểu quy định đeo thẻ trong tòa nhà.",
      "Đã biết khung giờ vào làm từ 8:00 đến 9:30 và cách báo khi vào muộn hoặc rời sớm.",
      "Đã biết cách đăng ký nghỉ phép qua HR Portal theo Chính sách nghỉ phép năm hiện hành.",
      "Đã đọc Chính sách phân loại dữ liệu và Chính sách mật khẩu và xác thực.",
      "Đã biết cách báo cáo sự cố bảo mật cho Trực SOC.",
      "Đã biết liên hệ HR Onboarding khi có câu hỏi về nội quy."),
    H2("Phụ lục C. Bảng tra cứu nhanh"),
    T(["Nội dung", "Quy định tóm tắt", "Văn bản chi tiết"], [
        ["Thời giờ làm việc", "8 giờ mỗi ngày, vào trong khung 8:00 đến 9:30, nghỉ trưa 1 giờ", "Nội quy lao động"],
        ["Vào muộn hơn 9:30", "Báo quản lý trước 9:30 cùng ngày và ghi HR Portal", "Nội quy lao động"],
        ["Thứ Bảy", "Làm việc từ xa theo phân công của quản lý", "Nội quy lao động"],
        ["Trang phục", "Theo Nội quy trang phục", "Nội quy trang phục"],
        ["Nghỉ phép", "Đăng ký qua HR Portal", "Chính sách nghỉ phép năm"],
        ["Bảo mật", "Không chia sẻ tài liệu Nội bộ trở lên ra ngoài", "Chính sách phân loại dữ liệu"],
        ["Sự cố bảo mật", "Báo Trực SOC trong 1 giờ", "Quy trình báo cáo sự cố bảo mật"],
    ], widths=[3, 6, 3.5]),
    H2("Phụ lục D. Đầu mối liên hệ"),
    T(["Nhu cầu", "Đầu mối", "Kênh"], [
        ["Câu hỏi về nội quy, khiếu nại", "HR Onboarding", "hr-onboarding@vsf-demo.example hoặc HR Portal"],
        ["Thẻ nhân viên, an toàn tòa nhà", "Facilities", "facilities@vsf-demo.example"],
        ["Thiết bị, tài khoản, VPN", "IT Helpdesk", "it-helpdesk@vsf-demo.example"],
        ["Sự cố bảo mật", "Trực SOC", "soc-oncall@vsf-demo.example"],
    ], widths=[4, 3, 5]),

    H1("Lịch sử sửa đổi"),
    T(["Phiên bản", "Ngày", "Nội dung thay đổi", "Người soạn"], [
        ["1.0", "01/01/2023", "Ban hành lần đầu, gồm các quy định về giờ làm việc, hình ảnh và xử lý vi phạm.", "Phòng Nhân sự"],
        ["2.0", "01/01/2024", "Bổ sung mục bảo mật thông tin và ứng xử nơi làm việc.", "Phòng Nhân sự"],
        ["3.0", "01/01/2025", "Điều chỉnh mục thời giờ làm việc linh hoạt và làm việc từ xa vào thứ Bảy; bổ sung ví dụ, bảng thời hạn báo, trình tự xử lý và câu hỏi thường gặp.", "Phòng Nhân sự"],
    ], widths=[1.8, 2.2, 6.5, 2.5]),
]

QA_D01 = [
    {"id": "L-D01-1", "q": "Nếu tôi chọn vào làm lúc 9:00 thì giờ ra tối thiểu là mấy giờ?", "must_include": ["18:00"], "docs": ["D01"]},
    {"id": "L-D01-2", "q": "Quy trình xử lý vi phạm nội quy cho tôi bao nhiêu ngày làm việc để giải trình?", "must_include": ["3 ngày làm việc để giải trình"], "docs": ["D01"]},
    {"id": "L-D01-3", "q": "Sau khi nhận quyết định xử lý, tôi có bao lâu để khiếu nại và Phòng Nhân sự phản hồi trong bao lâu?", "must_include": ["trong 5 ngày làm việc kể từ ngày nhận quyết định", "phản hồi trong 5 ngày làm việc"], "docs": ["D01"]},
    {"id": "L-D01-4", "q": "Quản lý phải thông báo danh sách người làm việc từ xa vào thứ Bảy chậm nhất khi nào?", "must_include": ["cuối ngày làm việc thứ Năm"], "docs": ["D01"]},
    {"id": "L-D01-5", "q": "Nếu không kịp báo trước 9:30 vì cấp cứu thì phải hoàn tất ghi nhận trên HR Portal khi nào?", "must_include": ["ngày làm việc kế tiếp"], "docs": ["D01"]},
]

# =====================================================================================================
# D02 - Nội quy trang phục
# =====================================================================================================
D02 = [
    H1("Thông tin kiểm soát tài liệu"),
    ctrl("SYN-D02", "Giám đốc Nhân sự", "Toàn bộ nhân sự làm việc tại văn phòng, kể cả nhân viên thử việc và thực tập sinh", "Đang hiệu lực"),

    H1("Mục đích và phạm vi"),
    H2("Mục đích"),
    P("Nội quy trang phục quy định mức yêu cầu tối thiểu về trang phục và hình ảnh của nhân sự khi làm việc tại văn phòng. Mục tiêu là giữ môi trường làm việc chuyên nghiệp, tạo ấn tượng tốt với khách hàng và đối tác, đồng thời tôn trọng sự thoải mái và phong cách cá nhân của từng người trong khuôn khổ chung."),
    H2("Phạm vi áp dụng"),
    P("Nội quy áp dụng cho mọi nhân sự có mặt tại khu vực làm việc của công ty, gồm nhân viên chính thức, nhân viên thử việc và thực tập sinh, tại tất cả các văn phòng. Nội quy cũng áp dụng khi nhân sự tham dự cuộc họp trực tuyến có bật camera với khách hàng hoặc đối tác bên ngoài. Khách đến làm việc được nhắc nhở nhẹ nhàng bởi đầu mối tiếp đón và không thuộc đối tượng bị xử lý theo nội quy này."),
    H2("Căn cứ và tài liệu liên quan"),
    B("Nội quy lao động: nguyên tắc chung, mục Trang phục và hình ảnh, yêu cầu đeo thẻ nhân viên trong tòa nhà và các mức xử lý vi phạm.",
      "Sổ tay nhân viên: phần tóm tắt quy định trang phục dành cho nhân sự mới.",
      "Chính sách làm việc từ xa: quy định về làm việc từ xa, trong đó có thứ Bảy làm việc từ xa theo phân công của quản lý."),
    P("Nếu có khác biệt giữa bản tóm tắt trong Sổ tay nhân viên và nội quy này, nội quy này là văn bản được ưu tiên đối với chi tiết về trang phục."),

    H1("Định nghĩa và thuật ngữ"),
    T(["Thuật ngữ", "Định nghĩa dùng trong nội quy này"], [
        ["Trang phục lịch sự", "Trang phục sạch sẽ, không rách, không nhàu, kín đáo, phù hợp môi trường làm việc chuyên nghiệp; đây là mức yêu cầu áp dụng hằng ngày."],
        ["Trang phục công sở", "Trang phục trang trọng hơn mức lịch sự thông thường, gồm áo sơ mi hoặc áo có cổ, áo vest hoặc áo khoác gọn, quần tây hoặc chân váy dài vừa phải, giày kín hoặc giày có quai hậu."],
        ["Ngày trang phục tự do (casual)", "Ngày nhân sự được mặc trang phục thoải mái hơn ngày thường nhưng vẫn phải gọn gàng, lịch sự và không thuộc nhóm bị cấm."],
        ["Khu vực làm việc", "Khu vực bàn làm việc, phòng họp, khu vực chung và khu vực tiếp khách trong văn phòng."],
        ["Đối tác bên ngoài", "Khách hàng, nhà cung cấp, cơ quan hoặc tổ chức không thuộc công ty đến làm việc hoặc họp với công ty."],
        ["Nội dung phản cảm", "Hình ảnh, chữ hoặc biểu tượng trên trang phục mang tính xúc phạm, kỳ thị, khiêu dâm, bạo lực hoặc gây tranh cãi về chính trị và tôn giáo."],
    ], widths=[3, 9]),

    H1("Vai trò và trách nhiệm"),
    T(["Vai trò", "Trách nhiệm chính", "Ghi chú"], [
        ["Nhân sự", "Tự giác mặc trang phục đúng nội quy, chuẩn bị trang phục công sở khi có lịch tiếp khách.", "Chịu trách nhiệm chính về trang phục của mình."],
        ["Quản lý trực tiếp", "Nhắc nhở lần đầu, thông báo lịch họp có đối tác để nhân sự chuẩn bị.", "Nhắc nhở riêng tư, không nhắc nhở công khai."],
        ["Phòng Nhân sự", "Sở hữu nội quy, giải đáp thắc mắc, giải quyết các trường hợp đặc biệt.", "Liên hệ HR Onboarding."],
        ["Ban Hành chính - Cơ sở vật chất (giả định)", "Nhắc nhở đầu mối tiếp đón và bảo vệ về quy định đối với khách.", "Liên hệ qua Facilities."],
    ], widths=[3, 6, 3.5]),

    H1("Nguyên tắc chung"),
    P("Nhân sự mặc trang phục lịch sự, gọn gàng khi làm việc tại văn phòng."),
    P("Nguyên tắc này dựa trên ba tiêu chí dễ kiểm tra: sạch sẽ và không rách, kín đáo ở mức phù hợp môi trường làm việc, và không mang nội dung phản cảm. Nội quy không quy định màu sắc, kiểu dáng hay thương hiệu, nên nhân sự có thể chọn phong cách riêng miễn đáp ứng các tiêu chí trên. Trong trường hợp nghi ngờ, nhân sự tự hỏi mình: nếu bất ngờ có cuộc họp với khách bên ngoài thì mình có thấy thoải mái ngồi vào bàn họp với trang phục này không."),
    P("Nhân sự cũng cần giữ vệ sinh cá nhân và hình thức gọn gàng. Thẻ nhân viên phải được đeo khi ở trong tòa nhà theo Nội quy lao động, và không được che khuất hoặc dán vật lạ lên thẻ."),

    H1("Trang phục không được phép"),
    P("Các loại trang phục sau không được mặc trong khu vực làm việc:"),
    B("Quần short hoặc váy quá ngắn trong khu vực làm việc.",
      "Dép lê, dép tông.",
      "Áo hai dây hoặc áo có nội dung phản cảm."),
    P("Để tránh hiểu sai, bảng dưới đây làm rõ cách áp dụng từng mục:"),
    T(["Trang phục", "Áp dụng thế nào", "Ví dụ"], [
        ["Quần short", "Không mặc quần short trong khu vực làm việc, kể cả vào ngày trang phục tự do.", "Quần short thể thao, quần đùi, quần lửng ngắn."],
        ["Váy quá ngắn", "Váy có độ dài không che kín đùi khi ngồi được coi là quá ngắn.", "Váy ngắn bó sát khi ngồi họp."],
        ["Dép lê, dép tông", "Không dùng khi ở trong khu vực làm việc; nên để giày hoặc dép có quai hậu tại chỗ ngồi.", "Dép xỏ ngón, dép nhựa đi trong nhà."],
        ["Áo hai dây", "Không mặc một mình; có thể mặc bên trong nếu có áo khoác hoặc áo choàng bên ngoài.", "Áo hai dây, áo ba lỗ mỏng."],
        ["Áo có nội dung phản cảm", "Không mặc áo có hình hoặc chữ thuộc nhóm nội dung phản cảm.", "Áo in lời lẽ xúc phạm hoặc hình ảnh bạo lực."],
    ], widths=[3, 5.5, 3.5]),
    P("Những trang phục không nằm trong danh sách trên nhưng gây mất tập trung hoặc không phù hợp môi trường làm việc có thể bị quản lý nhắc nhở theo tiêu chí lịch sự, gọn gàng. Danh sách này không phải là danh sách đầy đủ tuyệt đối; Phòng Nhân sự có quyền giải thích khi có tranh luận."),
    H2("Trường hợp ngoại lệ"),
    B("Nhân sự có lý do sức khỏe, tôn giáo hoặc văn hóa cần trang phục khác với quy định có thể trao đổi với Phòng Nhân sự để được xem xét bằng văn bản; quyết định được thông báo cho quản lý trực tiếp.",
      "Khi có sự kiện nội bộ do công ty tổ chức (ví dụ hoạt động gắn kết đội nhóm ngoài trời), trang phục theo thông báo của ban tổ chức.",
      "Khi trời mưa hoặc có sự cố bất khả kháng khiến trang phục bị ướt hoặc bẩn, nhân sự có thể thay thế tạm thời và báo cho quản lý; nếu chỉ là dép đi mưa, cần đổi sang giày hoặc dép có quai hậu khi đã vào chỗ ngồi."),

    H1("Thứ Sáu"),
    P("Thứ Sáu là ngày trang phục tự do (casual). Nhân sự vẫn phải giữ trang phục gọn gàng, lịch sự."),
    P("Ngày trang phục tự do cho phép nhân sự mặc thoải mái hơn, chẳng hạn áo thun có cổ hoặc không cổ, quần jean sạch, giày thể thao gọn gàng. Tuy nhiên, các loại trang phục nêu ở mục Trang phục không được phép vẫn bị cấm, kể cả vào thứ Sáu: nghĩa là ngày này không được mặc quần short, dép lê, dép tông hoặc áo có nội dung phản cảm."),
    P("Nếu thứ Sáu trùng với ngày nghỉ lễ theo lịch công ty công bố, nhân sự không cần chuẩn bị gì thêm. Nếu thứ Sáu có cuộc họp với đối tác bên ngoài, nhân sự áp dụng mục Tiếp khách và họp với đối tác bên dưới; quy định về ngày trang phục tự do không thay thế quy định này."),

    H1("Tiếp khách và họp với đối tác"),
    P("Khi tiếp khách hoặc họp với đối tác bên ngoài, nhân sự mặc trang phục công sở."),
    P("Quy định này áp dụng cho những người trực tiếp tham dự cuộc họp hoặc tiếp đón khách, kể cả khi cuộc họp diễn ra vào thứ Sáu. Đồng nghiệp không tham dự có thể tiếp tục mặc theo quy định thông thường trong ngày. Quản lý thông báo lịch họp có đối tác chậm nhất vào ngày làm việc trước đó để nhân sự kịp chuẩn bị; trường hợp khách đến đột xuất, nhân sự tham dự cố gắng điều chỉnh trang phục hợp lý trong khả năng."),
    P("Khi họp trực tuyến với đối tác bên ngoài có bật camera, nhân sự chỉ cần bảo đảm phần trang phục nhìn thấy trên màn hình đạt mức công sở. Nền phía sau nên gọn gàng và không hiện thông tin Nội bộ."),
    H2("Ví dụ minh họa"),
    P("Ví dụ 1. Nhân sự đến văn phòng vào thứ Sáu với áo thun có cổ và quần jean sạch. Đây là trang phục tự do hợp lệ. Nếu buổi chiều có cuộc họp với đối tác, nhân sự tham dự đổi sang áo sơ mi hoặc khoác thêm áo vest để đạt mức công sở."),
    P("Ví dụ 2. Nhân sự mặc quần short vào thứ Sáu vì trời nóng. Đây là trang phục không được phép, ngay cả trong ngày trang phục tự do. Quản lý nhắc nhở riêng và nhân sự cần thay bằng trang phục phù hợp."),
    P("Ví dụ 3. Nhân sự làm việc từ xa vào thứ Bảy theo phân công của quản lý và tham dự cuộc họp trực tuyến có khách. Nhân sự chỉ cần bảo đảm phần trang phục hiển thị trên camera đạt mức công sở, không cần mặc đầy đủ trang phục công sở từ đầu đến chân."),

    H1("Nhắc nhở và xử lý"),
    P("Việc nhắc nhở nhằm giúp nhân sự điều chỉnh, không nhằm làm khó. Quản lý trực tiếp là người nhắc nhở đầu tiên, thực hiện riêng tư và ngắn gọn. Quy trình gồm ba bước:"),
    N("Nhắc nhở miệng: quản lý trao đổi riêng, nêu rõ nội dung chưa phù hợp và đề nghị điều chỉnh ngay trong ngày.",
      "Ghi nhận: nếu nhân sự tái phạm hoặc không điều chỉnh, quản lý ghi nhận ngắn gọn và thông báo cho Phòng Nhân sự.",
      "Xử lý theo Nội quy lao động: Phòng Nhân sự xem xét mức độ vi phạm. Vi phạm lần đầu, không gây hậu quả thường là mức nhẹ; tái phạm nhiều lần hoặc mặc trang phục có nội dung phản cảm gây ảnh hưởng đến đồng nghiệp được xem xét ở mức trung bình."),
    P("Nhân sự không đồng ý với việc nhắc nhở có thể trao đổi với quản lý cấp cao hơn hoặc liên hệ HR Onboarding qua hr-onboarding@vsf-demo.example."),

    H1("Câu hỏi thường gặp"),
    P("Hỏi: Thứ Sáu tôi có được mặc quần short không? Đáp: Không. Thứ Sáu là ngày trang phục tự do, nhưng quần short vẫn nằm trong nhóm trang phục không được phép tại khu vực làm việc."),
    P("Hỏi: Thứ Sáu tôi có cuộc họp với đối tác thì mặc gì? Đáp: Khi họp với đối tác bên ngoài, bạn mặc trang phục công sở, kể cả khi hôm đó là thứ Sáu."),
    P("Hỏi: Tôi có thể đi giày thể thao vào ngày thường không? Đáp: Được, miễn là giày sạch, gọn gàng và bạn đáp ứng nguyên tắc trang phục lịch sự. Nội quy chỉ cấm dép lê và dép tông."),
    P("Hỏi: Áo hai dây mặc bên trong áo khoác có được không? Đáp: Được nếu bạn khoác áo bên ngoài và không tháo ra trong khu vực làm việc. Mặc áo hai dây một mình thì không được phép."),
    P("Hỏi: Nội quy có quy định màu sắc hay thương hiệu không? Đáp: Không. Nội quy chỉ yêu cầu lịch sự, gọn gàng và không có nội dung phản cảm."),
    P("Hỏi: Khi làm việc từ xa vào thứ Bảy tôi có phải mặc trang phục công sở không? Đáp: Không cần, trừ khi bạn tham dự họp trực tuyến có bật camera với đối tác bên ngoài; khi đó phần trang phục hiển thị trên camera cần đạt mức công sở."),
    P("Hỏi: Nếu tôi bị nhắc nhở nhiều lần thì sao? Đáp: Quản lý sẽ ghi nhận và thông báo cho Phòng Nhân sự để xem xét theo các mức xử lý trong Nội quy lao động."),
    P("Hỏi: Tôi có lý do tôn giáo cần mặc trang phục khác quy định thì làm sao? Đáp: Bạn trao đổi với Phòng Nhân sự để được xem xét và nhận văn bản xác nhận."),

    H1("Phụ lục"),
    H2("Phụ lục A. Danh sách tự kiểm tra trước khi đến văn phòng"),
    B("Trang phục sạch sẽ, không rách và không nhàu.",
      "Không mặc quần short, váy quá ngắn, dép lê, dép tông hoặc áo hai dây.",
      "Áo không có nội dung phản cảm.",
      "Thẻ nhân viên đeo ở vị trí dễ thấy khi vào tòa nhà.",
      "Nếu có cuộc họp hoặc tiếp khách bên ngoài: đã chuẩn bị trang phục công sở."),
    H2("Phụ lục B. Bảng tra cứu nhanh theo ngày và hoàn cảnh"),
    T(["Hoàn cảnh", "Mức trang phục", "Lưu ý"], [
        ["Thứ Hai đến thứ Năm, không có khách", "Lịch sự, gọn gàng", "Không mặc loại trang phục bị cấm"],
        ["Thứ Sáu, không có khách", "Trang phục tự do (casual)", "Vẫn gọn gàng, lịch sự và không mặc loại bị cấm"],
        ["Có khách hoặc họp với đối tác, kể cả thứ Sáu", "Công sở", "Áp dụng cho người tham dự"],
        ["Họp trực tuyến có bật camera với đối tác", "Công sở phần hiển thị trên camera", "Nền gọn gàng, không hiện thông tin Nội bộ"],
        ["Thứ Bảy làm việc từ xa", "Lịch sự, gọn gàng khi bật camera", "Không cần mặc công sở đầy đủ"],
    ], widths=[4.5, 4, 3.5]),
    H2("Phụ lục C. Mẫu nhắc nhở nhẹ nhàng"),
    P("Nội dung mẫu quản lý có thể dùng khi nhắc nhở riêng: 'Chào bạn, mình nhận thấy trang phục hôm nay chưa phù hợp với Nội quy trang phục. Bạn vui lòng điều chỉnh trong hôm nay nhé. Nếu có khó khăn, bạn cứ trao đổi với mình hoặc với HR Onboarding.'"),

    H1("Lịch sử sửa đổi"),
    T(["Phiên bản", "Ngày", "Nội dung thay đổi", "Người soạn"], [
        ["1.0", "01/06/2024", "Ban hành lần đầu, nêu nguyên tắc chung và danh sách trang phục không được phép.", "Phòng Nhân sự"],
        ["1.1", "01/03/2025", "Bổ sung quy định ngày trang phục tự do vào thứ Sáu, quy định khi tiếp khách và họp với đối tác, ví dụ minh họa, bảng tra cứu và câu hỏi thường gặp.", "Phòng Nhân sự"],
    ], widths=[1.8, 2.2, 6.5, 2.5]),
]

QA_D02 = [
    {"id": "L-D02-1", "q": "Nếu tôi có cuộc họp với đối tác vào thứ Sáu thì có được mặc trang phục tự do không?", "must_include": ["kể cả khi hôm đó là thứ Sáu"], "docs": ["D02"]},
    {"id": "L-D02-2", "q": "Mặc áo hai dây bên trong áo khoác có vi phạm nội quy trang phục không?", "must_include": ["Mặc áo hai dây một mình thì không được phép"], "docs": ["D02"]},
    {"id": "L-D02-3", "q": "Khi họp trực tuyến có khách bật camera thì trang phục phải đạt mức nào?", "must_include": ["phần trang phục nhìn thấy trên màn hình đạt mức công sở"], "docs": ["D02"]},
    {"id": "L-D02-4", "q": "Quy trình nhắc nhở khi mặc sai quy định trang phục gồm những bước nào?", "must_include": ["Nhắc nhở miệng", "Ghi nhận"], "docs": ["D02"]},
]

# =====================================================================================================
# D03a / D03b / D03c - Chính sách nghỉ phép năm (ba phiên bản dùng chung một khung, chỉ khác dữ kiện)
# =====================================================================================================
def _leave_doc(c):
    full = c["full"]
    hr_lp = c["long_leave"]  # có quy tắc trưởng phòng phê duyệt kỳ nghỉ dài hay không
    out = []
    basis = ["Bộ luật Lao động 2019 (45/2019/QH14): quy định pháp luật về nghỉ hằng năm, là mức tối thiểu mà chính sách này phải bảo đảm.",
             "Nội quy lao động: nguyên tắc chung về giờ làm việc, vắng mặt và xử lý vi phạm.",
             "Chính sách thử việc: quyền lợi của nhân viên trong thời gian thử việc."]
    if full:
        basis += ["Chính sách phúc lợi và bảo hiểm: các quyền lợi khác không thuộc phạm vi phép năm.",
                  "Sổ tay nhân viên: tóm tắt cách đăng ký nghỉ phép dành cho nhân sự mới."]

    # ---------------------------------------------------------------- 1. kiểm soát tài liệu
    out += [
        H1("Thông tin kiểm soát tài liệu"),
        ctrl(c["code"], "Giám đốc Nhân sự",
             "Nhân viên chính thức của công ty; nhân viên thử việc và thực tập sinh không thuộc đối tượng hưởng phép năm",
             c["status"], extra=[["Thời gian áp dụng", c["period"]]]),
        P(c["ctrl_note"]),
    ]

    # ---------------------------------------------------------------- 2. mục đích và phạm vi
    out += [
        H1("Mục đích và phạm vi"),
        H2("Mục đích"),
        P("Chính sách này quy định số ngày phép năm có lương, cách tính thâm niên, cách đăng ký, phê duyệt và sử dụng phép năm, cùng điều kiện chuyển phép sang năm sau. Mục tiêu là bảo đảm quyền nghỉ ngơi của nhân viên, đồng thời giúp quản lý sắp xếp công việc chủ động và công bằng giữa các thành viên trong đội."),
        H2("Phạm vi và đối tượng áp dụng"),
        P("Chính sách áp dụng cho nhân viên chính thức của công ty tại mọi văn phòng. Nhân viên thử việc và thực tập sinh không thuộc đối tượng của chính sách này; quy định dành cho nhân viên thử việc nằm trong Chính sách thử việc. Chính sách chỉ điều chỉnh phép năm có lương; các loại nghỉ khác do pháp luật lao động và văn bản riêng quy định."),
        H2("Căn cứ và tài liệu liên quan"),
        B(*basis),
        H2("Hiệu lực của phiên bản"),
        P(c["effect_txt"]),
    ]
    if full:
        out.append(P("Khi một kỳ nghỉ kéo dài qua ngày chuyển đổi phiên bản hoặc chuyển năm phép, phiên bản áp dụng được xác định theo ngày nghỉ đầu tiên của kỳ nghỉ, còn số ngày phép bị trừ vào năm phép chứa từng ngày nghỉ. Phòng Nhân sự có trách nhiệm hướng dẫn cụ thể khi phát sinh trường hợp này."))

    # ---------------------------------------------------------------- 3. định nghĩa
    defs = [
        ["Phép năm", "Số ngày nghỉ có hưởng lương mà nhân viên chính thức được hưởng trong một năm phép."],
        ["Năm phép", "Khoảng thời gian từ ngày 01/01 đến ngày 31/12 hằng năm."],
        ["Nhân viên chính thức", "Nhân sự đã hoàn thành thử việc và có hợp đồng lao động chính thức."],
        ["Nhân viên thử việc", "Nhân sự đang trong thời gian thử việc theo Chính sách thử việc."],
        ["Ngày làm việc", "Các ngày từ thứ Hai đến thứ Sáu, không kể ngày nghỉ lễ theo lịch công ty công bố."],
        ["Thâm niên", "Thời gian làm việc liên tục tại công ty, tính từ ngày bắt đầu làm việc đến ngày 01/01 của năm phép, chỉ lấy số năm đủ."],
        ["Quản lý trực tiếp", "Người quản lý công việc hằng ngày của nhân viên, là người xem xét đơn nghỉ phép đầu tiên."],
        ["Trưởng phòng", "Người đứng đầu đơn vị mà nhân viên trực thuộc."],
        ["HR Portal", "Cổng thông tin nhân sự nội bộ, nơi nhân viên đăng ký nghỉ phép, theo dõi số dư và kết quả phê duyệt."],
        ["Ngày phép chuyển", "Số ngày phép năm chưa dùng hết được đưa sang năm phép kế tiếp theo điều kiện của chính sách."],
        ["Nửa ngày phép", "Nghỉ một buổi sáng hoặc một buổi chiều, tính bằng 0,5 ngày phép và tương ứng khoảng 4 giờ làm việc."],
    ]
    if not full:
        defs = [d for d in defs if d[0] not in ("Quản lý trực tiếp", "Trưởng phòng")]
    if hr_lp:
        defs.append(["Nghỉ liên tục", "Một đợt nghỉ gồm các ngày phép bị trừ, không bị ngắt quãng bởi ngày làm việc đi làm. Ngày nghỉ cuối tuần và ngày nghỉ lễ nằm xen giữa không được cộng vào số ngày phép nhưng không làm đứt tính liên tục."])
    out += [H1("Định nghĩa và thuật ngữ"), T(["Thuật ngữ", "Định nghĩa dùng trong chính sách này"], defs, widths=[3, 9])]

    # ---------------------------------------------------------------- 4. vai trò
    if hr_lp:
        mgr = "Xem xét và phê duyệt đơn nghỉ phép dưới 5 ngày liên tục, sắp xếp người thay thế, bảo đảm công việc không bị gián đoạn."
        tp = "Phê duyệt đơn nghỉ phép từ 5 ngày liên tục trở lên; xem xét khi lịch nghỉ giữa các thành viên xung đột."
    else:
        mgr = "Xem xét và phê duyệt mọi đơn nghỉ phép của thành viên trong đội, sắp xếp người thay thế, bảo đảm công việc không bị gián đoạn."
        tp = "Xem xét khi lịch nghỉ giữa các thành viên xung đột hoặc khi quản lý trực tiếp không thể phê duyệt."
    out += [
        H1("Vai trò và trách nhiệm"),
        T(["Vai trò", "Trách nhiệm chính", "Ghi chú"], [
            ["Nhân viên chính thức", "Theo dõi số dư phép, đăng ký đúng thời hạn, bàn giao công việc trước khi nghỉ.", "Chịu trách nhiệm chính về đăng ký."],
            ["Quản lý trực tiếp", mgr, "Phản hồi trên HR Portal."],
            ["Trưởng phòng", tp, "Phối hợp với Phòng Nhân sự."],
            ["Phòng Nhân sự", "Cập nhật số dư phép, giải đáp thắc mắc, lưu hồ sơ và xử lý khiếu nại.", "Là đơn vị sở hữu chính sách."],
        ] + ([["HR Onboarding", "Hỗ trợ nhân sự mới làm quen cách đăng ký nghỉ phép.", "hr-onboarding@vsf-demo.example"]] if full else []), widths=[3, 6.5, 3.5]),
    ]

    # ---------------------------------------------------------------- 5. số ngày phép năm
    out += [H1("Số ngày phép năm"), H2("Mức hưởng"), P(c["base_txt"]),
            P("Phép năm là ngày nghỉ hưởng nguyên lương. Số ngày phép của một năm phép được ghi nhận vào ngày 01/01 hằng năm và hiển thị trên HR Portal; nhân viên có thể tự kiểm tra số dư bất cứ lúc nào.")]
    out += [
        H2("Tính theo tỷ lệ trong năm đầu"),
        P("Nhân viên trở thành nhân viên chính thức giữa năm phép được hưởng phép theo tỷ lệ số tháng còn lại. Tháng trở thành nhân viên chính thức được tính đủ nếu ngày đó nằm ở nửa đầu tháng; nếu nằm ở nửa sau tháng thì tính từ tháng kế tiếp. Kết quả được làm tròn xuống đến 0,5 ngày."),
        P(c["pro_ex"]),
    ]
    out += [
        H2("Cách tính ngày nghỉ"),
        P("Chỉ những ngày làm việc nằm trong kỳ nghỉ mới bị trừ vào phép năm. Thứ Bảy, Chủ nhật và ngày nghỉ lễ theo lịch công ty công bố không bị trừ. Nhân viên có tên trong phân công làm việc từ xa vào thứ Bảy mà xin nghỉ vào ngày đó phải thống nhất với quản lý về việc bù nghỉ; thứ Bảy không thuộc phân công thì không cần xin nghỉ. Nhân viên được nghỉ nửa ngày, mỗi lần trừ 0,5 ngày phép."),
    ]
    if full:
        out += [
            H2("Bảng tình huống thường gặp"),
            T(["Tình huống", "Cách tính", "Kết quả"], [
                ["Nghỉ từ thứ Hai đến thứ Sáu", "5 ngày làm việc", "Trừ 5 ngày phép"],
                ["Nghỉ từ thứ Năm tuần này đến thứ Ba tuần sau", "Thứ Năm, thứ Sáu, thứ Hai, thứ Ba", "Trừ 4 ngày phép; thứ Bảy và Chủ nhật không trừ"],
                ["Nghỉ buổi chiều thứ Sáu", "Nửa ngày", "Trừ 0,5 ngày phép"],
                ["Nghỉ có một ngày lễ nằm giữa kỳ nghỉ", "Ngày lễ không phải ngày làm việc", "Không trừ phép cho ngày lễ"],
            ], widths=[4.5, 4, 3.5]),
        ]

    # ---------------------------------------------------------------- 6. thâm niên
    out += [
        H1("Thâm niên công tác"),
        P("Nhân viên có thâm niên từ 5 năm trở lên được cộng thêm 1 ngày phép cho mỗi 5 năm làm việc liên tục."),
        P("Thâm niên được xác định vào ngày 01/01 của năm phép và chỉ tính số năm đủ, không làm tròn lên. Số ngày cộng thêm là phần bổ sung vào mức phép năm cơ bản và được ghi nhận cùng lúc với phép năm của năm đó. Bảng dưới đây cho biết số ngày cộng thêm theo số năm thâm niên đủ:"),
        T(["Số năm thâm niên đủ", "Số ngày cộng thêm", "Ghi chú"], [
            ["Dưới 5 năm", "0 ngày", "Chỉ hưởng mức phép năm cơ bản"],
            ["Từ 5 đến dưới 10 năm", "1 ngày", "Một lần cộng"],
            ["Từ 10 đến dưới 15 năm", "2 ngày", "Hai lần cộng"],
            ["Từ 15 đến dưới 20 năm", "3 ngày", "Ba lần cộng"],
            ["Từ 20 năm trở lên", "4 ngày", "Tiếp tục cộng thêm 1 ngày cho mỗi 5 năm đủ"],
        ], widths=[4, 3, 5]),
        P(c["sen_ex"]),
    ]

    # ---------------------------------------------------------------- 7. quy định sử dụng
    out += [H1("Quy định sử dụng"), H2("Đăng ký và thời hạn báo trước"), P(c["reg_txt"]),
            P(c["reg_extra"])]
    if hr_lp:
        out += [
            H2("Phê duyệt và kỳ nghỉ dài"),
            P("Đơn nghỉ phép dưới 5 ngày liên tục do quản lý trực tiếp phê duyệt. Đơn nghỉ từ 5 ngày liên tục trở lên phải được trưởng phòng phê duyệt sau khi quản lý trực tiếp xác nhận đã sắp xếp được người thay thế. Số ngày liên tục được tính theo số ngày phép bị trừ trong một đợt nghỉ; ngày nghỉ cuối tuần và ngày nghỉ lễ nằm xen giữa không làm đứt tính liên tục nhưng cũng không được cộng vào số ngày."),
        ]
        if full:
            out.append(P("Nếu nhân viên chia một đợt nghỉ dài thành nhiều đơn ngắn liền nhau nhằm tránh cấp phê duyệt cao hơn, các đơn đó được gộp lại để xác định cấp phê duyệt."))
    else:
        out += [
            H2("Phê duyệt"),
            P("Mọi đơn nghỉ phép do quản lý trực tiếp phê duyệt trên HR Portal. Quản lý có quyền đề nghị nhân viên lùi hoặc chia lại kỳ nghỉ khi có công việc quan trọng đã được lên kế hoạch từ trước; đề nghị này phải nêu lý do và không được kéo dài bất hợp lý quyền nghỉ của nhân viên."),
        ]
    out += [
        H2("Chuyển phép sang năm sau"),
        P(c["carry_txt"]),
        P(c["carry_ex"]),
    ]
    if c["cash"]:
        out += [
            H2("Thanh toán bằng tiền"),
            P("Yêu cầu thanh toán được gửi qua HR Portal, nêu số ngày phép còn lại muốn thanh toán. Đối với phần vượt mức được chuyển sang năm sau, nhân viên gửi yêu cầu chậm nhất vào ngày 31/12. Đối với phần đã chuyển sang năm sau, nhân viên gửi yêu cầu chậm nhất vào ngày 31/03. Phòng Nhân sự chi trả trong kỳ trả lương kế tiếp sau khi yêu cầu được xác nhận. Ngày phép đã hết hạn mà không có yêu cầu thanh toán thì không còn giá trị sử dụng."),
        ]
    if full:
      out += [
        H2("Thay đổi hoặc hủy đơn"),
        P("Nhân viên có thể sửa hoặc hủy đơn nghỉ phép trên HR Portal trước ngày nghỉ ít nhất 1 ngày làm việc. Đơn đã hủy thì số ngày phép được hoàn lại vào số dư ngay sau khi Phòng Nhân sự cập nhật. Khi nhu cầu thay đổi đột xuất trong vòng 1 ngày làm việc trước ngày nghỉ, nhân viên liên hệ trực tiếp quản lý để được xem xét."),
        H2("Trường hợp không kịp thời hạn đăng ký"),
        P("Trường hợp có việc gia đình hoặc sự cố khẩn cấp không thể đăng ký kịp thời hạn, nhân viên báo ngay cho quản lý trực tiếp bằng kênh liên lạc bất kỳ và bổ sung đơn trên HR Portal trong ngày làm việc kế tiếp. Nếu quản lý xác nhận lý do chính đáng, đơn được xét như đăng ký đúng hạn; nếu không, những ngày vắng mặt chưa được phê duyệt bị xem là nghỉ không phép theo Nội quy lao động."),
    ]

    # ---------------------------------------------------------------- 8. đối tượng không áp dụng
    out += [H1("Đối tượng không áp dụng"), P("Nhân viên thử việc không được nghỉ phép năm, xem Chính sách thử việc."),
            P("Thực tập sinh không thuộc đối tượng hưởng phép năm theo chính sách này. Việc nghỉ của thực tập sinh do đơn vị tiếp nhận và Phòng Nhân sự thống nhất theo thỏa thuận thực tập.")]
    if full:
        out.append(P("Khi nhân viên thôi việc, số ngày phép còn lại của năm phép hiện tại được xử lý theo quy định của pháp luật lao động và hướng dẫn của Phòng Nhân sự tại thời điểm chấm dứt hợp đồng."))

    # ---------------------------------------------------------------- 9. quy trình từng bước
    out += [
        H1("Quy trình đăng ký nghỉ phép"),
        N("Kiểm tra số dư phép trên HR Portal, gồm phép của năm hiện tại, số ngày cộng thêm theo thâm niên và số ngày phép chuyển (nếu có).",
          "Thống nhất sơ bộ thời gian nghỉ và người thay thế với quản lý trực tiếp và đồng nghiệp trong đội.",
          "Đăng ký nghỉ phép trên HR Portal, nêu ngày bắt đầu, ngày kết thúc, loại nghỉ (cả ngày hoặc nửa ngày) và người bàn giao công việc, bảo đảm đúng thời hạn báo trước.",
          c["step_appr"],
          "Nhận kết quả phê duyệt trên HR Portal. Nếu bị từ chối, nhân viên nhận lý do bằng văn bản và có thể điều chỉnh thời gian nghỉ.",
          "Bàn giao công việc, đặt trả lời tự động khi nghỉ và thực hiện kỳ nghỉ.",
          "Sau kỳ nghỉ, kiểm tra lại số dư phép trên HR Portal; nếu sai lệch, liên hệ Phòng Nhân sự."),
        H1("Thời hạn xử lý"),
        T(["Bước", "Thời hạn", "Bên thực hiện"], [
            ["Đăng ký nghỉ phép", "Trước ngày nghỉ ít nhất " + c["adv"], "Nhân viên"],
            ["Quản lý trực tiếp phản hồi", "Trong 1 ngày làm việc kể từ khi nhận đơn", "Quản lý trực tiếp"],
        ] + ([["Trưởng phòng phản hồi (kỳ nghỉ từ 5 ngày liên tục trở lên)", "Trong 2 ngày làm việc kể từ khi quản lý xác nhận", "Trưởng phòng"]] if hr_lp else []) + [
            ["Cập nhật số dư phép", "Trong 1 ngày làm việc kể từ khi đơn được phê duyệt", "Phòng Nhân sự"],
        ] + ([["Hủy hoặc sửa đơn", "Trước ngày nghỉ ít nhất 1 ngày làm việc", "Nhân viên"]] if full else []) + ([["Yêu cầu thanh toán bằng tiền", "Chậm nhất ngày 31/12 hoặc 31/03 tùy phần phép", "Nhân viên"]] if c["cash"] else []), widths=[5, 4.5, 2.5]),
        P("Nếu quá thời hạn phản hồi mà đơn chưa được xử lý, nhân viên nhắc lại trên HR Portal hoặc liên hệ HR Onboarding. Đơn chưa được phê duyệt không được xem là đã được đồng ý, vì vậy nhân viên không tự nghỉ khi chưa có kết quả."),
    ]

    # ---------------------------------------------------------------- 10. vi phạm, khiếu nại
    out += [
        H1("Khiếu nại và xử lý vi phạm"),
        P("Nhân viên nghỉ mà chưa được phê duyệt, khai báo sai số ngày nghỉ hoặc dùng phép của người khác bị xử lý theo Nội quy lao động, mức độ do Phòng Nhân sự xác định. Nhân viên không đồng ý với việc từ chối đơn hoặc với số dư phép ghi nhận có thể gửi khiếu nại tới hr-onboarding@vsf-demo.example hoặc HR Portal trong 5 ngày làm việc kể từ ngày nhận kết quả. Phòng Nhân sự phản hồi trong 5 ngày làm việc kể từ ngày nhận đủ thông tin."),
    ]

    # ---------------------------------------------------------------- 11. câu hỏi thường gặp
    out.append(H1("Câu hỏi thường gặp"))
    out += [P(x) for x in c["faq"]]

    # ---------------------------------------------------------------- 12. phụ lục
    out += [
        H1("Phụ lục"),
        H2("Phụ lục A. Mẫu email thông báo kế hoạch nghỉ phép"),
        P("Gửi cho quản lý trực tiếp và đồng nghiệp liên quan sau khi đơn được phê duyệt. Nội dung mẫu: 'Kính gửi anh chị, em nghỉ phép năm từ ngày [bắt đầu] đến hết ngày [kết thúc]. Trong thời gian này, [tên người thay thế] sẽ hỗ trợ các việc đang thực hiện. Em sẽ quay lại làm việc vào ngày [ngày quay lại].'"),
        H2("Phụ lục B. Danh sách kiểm tra trước khi nghỉ"),
        B("Đã kiểm tra số dư phép trên HR Portal.",
          "Đã đăng ký đúng thời hạn báo trước " + c["adv"] + ".",
          "Đã có người thay thế và đã bàn giao các việc đang thực hiện.",
          "Đã nhận kết quả phê duyệt trên HR Portal.",
          "Đã đặt trả lời tự động và thông báo cho đồng nghiệp liên quan."),
        H2("Phụ lục C. Bảng tra cứu nhanh"),
        T(["Nội dung", "Quy định"], [
            ["Số ngày phép năm cơ bản", c["base"]],
            ["Cộng thêm theo thâm niên", "1 ngày cho mỗi 5 năm làm việc liên tục, từ 5 năm trở lên"],
            ["Thời hạn đăng ký", "Trước ít nhất " + c["adv"]],
            ["Chuyển phép sang năm sau", c["carry_short"]],
            ["Nhân viên thử việc", "Không được nghỉ phép năm"],
        ], widths=[5, 7]),
    ]
    if full:
        out += [
            H2("Phụ lục D. Ví dụ tính số dư phép"),
            P(c["balance_ex"]),
        ]

    # ---------------------------------------------------------------- 13. lịch sử sửa đổi
    out += [H1("Lịch sử sửa đổi"), T(["Phiên bản", "Ngày", "Nội dung thay đổi", "Người soạn"], c["history"], widths=[1.8, 2.2, 6.5, 2.5])]
    return out


# ------------------------------------------------------------------------------------------ dữ kiện từng phiên bản
_CFG_A = dict(
    key="a", code="SYN-D03a", full=False, long_leave=False, cash=False,
    status="Đã hết hiệu lực từ ngày 01/01/2024 (áp dụng đến hết ngày 31/12/2023)",
    period="Từ ngày 01/01/2023 đến hết ngày 31/12/2023",
    ctrl_note="Đây là phiên bản 2023 của Chính sách nghỉ phép năm. Phiên bản này đã hết hiệu lực vào ngày 31/12/2023 và chỉ dùng để tra cứu cho các kỳ nghỉ phát sinh trong thời gian phiên bản còn hiệu lực. Từ ngày 01/01/2024, nhân sự áp dụng phiên bản kế tiếp của chính sách này.",
    effect_txt="Phiên bản này có hiệu lực từ ngày 01/01/2023 đến hết ngày 31/12/2023. Kỳ nghỉ bắt đầu sau ngày 31/12/2023 không áp dụng phiên bản này.",
    base="10 ngày", adv="3 ngày làm việc",
    base_txt="Mỗi nhân viên chính thức được hưởng 10 ngày phép năm có lương.",
    pro_ex="Ví dụ 1. Nhân viên trở thành nhân viên chính thức từ ngày 01/07, còn 6 tháng trong năm phép. Số phép được hưởng bằng 10 ngày nhân 6 chia 12, tương đương 5 ngày phép. Ví dụ 2. Nhân viên trở thành nhân viên chính thức từ ngày 20/07, thuộc nửa sau tháng nên tính từ tháng 8, còn 5 tháng. Số phép bằng 10 ngày nhân 5 chia 12, làm tròn xuống thành 4 ngày phép.",
    sen_ex="Ví dụ. Nhân viên có 7 năm thâm niên đủ vào ngày 01/01 được cộng thêm 1 ngày phép, tổng cộng 11 ngày phép năm. Nhân viên có 4 năm 11 tháng thâm niên chưa được cộng thêm ngày nào vì chưa đủ 5 năm.",
    reg_txt="Phép năm phải được đăng ký trước ít nhất 3 ngày làm việc. Phép năm không sử dụng hết được chuyển tối đa 3 ngày sang năm sau.",
    reg_extra="Việc đăng ký được thực hiện trên HR Portal, nêu rõ ngày nghỉ, loại nghỉ và người thay thế. Thời hạn báo trước tính theo ngày làm việc, không tính ngày nộp đơn, ngày nghỉ đầu tiên, ngày nghỉ cuối tuần và ngày nghỉ lễ. Ví dụ, nhân viên muốn nghỉ vào thứ Sáu cần gửi đơn chậm nhất vào thứ Hai của tuần đó. Nhân viên muốn nghỉ vào thứ Hai cần gửi đơn chậm nhất vào thứ Ba của tuần trước, vì thứ Bảy và Chủ nhật không được tính.",
    carry_txt="Phép năm không sử dụng hết được chuyển tối đa 3 ngày sang năm sau. Số ngày phép chuyển phải được sử dụng trong năm phép kế tiếp và không được chuyển tiếp lần thứ hai. Phần vượt quá số ngày được chuyển không còn giá trị sử dụng. Chính sách này không có cơ chế thanh toán bằng tiền cho ngày phép chưa dùng, trừ trường hợp pháp luật lao động có yêu cầu.",
    carry_ex="Ví dụ. Cuối năm nhân viên còn 4 ngày phép chưa dùng. Nhân viên được chuyển 3 ngày sang năm sau; ngày phép còn lại không còn giá trị sử dụng.",
    carry_short="Tối đa 3 ngày, dùng trong năm kế tiếp",
    step_appr="Quản lý trực tiếp xem xét và phê duyệt đơn trên HR Portal, hoặc đề nghị điều chỉnh thời gian nếu có công việc quan trọng.",
    balance_ex="",
    faq=[
        "Hỏi: Nhân viên chính thức được nghỉ phép năm bao nhiêu ngày? Đáp: Mỗi nhân viên chính thức được hưởng 10 ngày phép năm có lương, chưa gồm số ngày cộng thêm theo thâm niên.",
        "Hỏi: Tôi phải đăng ký nghỉ phép trước bao lâu? Đáp: Phép năm phải được đăng ký trước ít nhất 3 ngày làm việc, thực hiện trên HR Portal.",
        "Hỏi: Tôi còn 4 ngày phép cuối năm thì được chuyển mấy ngày sang năm sau? Đáp: Tối đa 3 ngày; ngày còn lại không còn giá trị sử dụng.",
        "Hỏi: Ai phê duyệt đơn nghỉ phép của tôi? Đáp: Quản lý trực tiếp phê duyệt mọi đơn nghỉ phép trên HR Portal trong 1 ngày làm việc.",
        "Hỏi: Nhân viên thử việc có được nghỉ phép năm không? Đáp: Không. Nhân viên thử việc không được nghỉ phép năm, xem Chính sách thử việc.",
        "Hỏi: Tôi có được nghỉ nửa ngày không? Đáp: Có. Nhân viên được nghỉ nửa ngày, mỗi lần trừ 0,5 ngày phép.",
        "Hỏi: Thứ Bảy và Chủ nhật nằm trong kỳ nghỉ có bị trừ phép không? Đáp: Không. Chỉ những ngày làm việc nằm trong kỳ nghỉ mới bị trừ vào phép năm.",
        "Hỏi: Tôi vào làm chính thức giữa năm thì được bao nhiêu phép? Đáp: Được hưởng theo tỷ lệ số tháng còn lại trong năm phép, làm tròn xuống đến 0,5 ngày.",
    ],
    history=[
        ["1.0", "01/01/2023", "Ban hành lần đầu chính sách nghỉ phép năm, gồm mức phép năm, thâm niên, quy định đăng ký và chuyển phép.", "Phòng Nhân sự"],
    ],
)

_CFG_B = dict(
    key="b", code="SYN-D03b", full=True, long_leave=True, cash=True,
    status="Đang hiệu lực",
    period="Từ ngày 01/01/2024 cho đến khi có phiên bản thay thế",
    ctrl_note="Đây là phiên bản 2024 của Chính sách nghỉ phép năm, có hiệu lực kể từ ngày 01/01/2024. Nhân sự cần dùng phiên bản có hiệu lực tại ngày dự kiến nghỉ; khi có phiên bản mới với ngày hiệu lực trong tương lai, phiên bản này vẫn được áp dụng cho đến trước ngày hiệu lực đó.",
    effect_txt="Phiên bản này có hiệu lực từ ngày 01/01/2024 và thay thế hoàn toàn phiên bản 1.0 kể từ ngày đó. Kỳ nghỉ bắt đầu từ ngày 01/01/2024 áp dụng chính sách này cho đến khi có phiên bản thay thế.",
    base="12 ngày", adv="2 ngày làm việc",
    base_txt="Mỗi nhân viên chính thức được hưởng 12 ngày phép năm có lương, tăng so với chính sách năm 2023. Chính sách này thay thế hoàn toàn phiên bản 1.0.",
    pro_ex="Ví dụ 1. Nhân viên trở thành nhân viên chính thức từ ngày 01/07, còn 6 tháng trong năm phép. Số phép được hưởng bằng 12 ngày nhân 6 chia 12, tương đương 6 ngày phép. Ví dụ 2. Nhân viên trở thành nhân viên chính thức từ ngày 20/07, thuộc nửa sau tháng nên tính từ tháng 8, còn 5 tháng. Số phép bằng 12 ngày nhân 5 chia 12, tương đương 5 ngày phép.",
    sen_ex="Ví dụ: nhân viên có 10 năm thâm niên được 14 ngày phép (12 + 2). Nhân viên có 7 năm thâm niên đủ vào ngày 01/01 được cộng thêm 1 ngày phép vào mức cơ bản. Nhân viên có 4 năm 11 tháng thâm niên chưa được cộng thêm ngày nào vì chưa đủ 5 năm.",
    reg_txt="Phép năm phải được đăng ký trước ít nhất 2 ngày làm việc qua HR Portal. Nghỉ phép từ 5 ngày liên tục trở lên cần được trưởng phòng phê duyệt.",
    reg_extra="Đơn đăng ký nêu rõ ngày nghỉ, loại nghỉ và người thay thế. Thời hạn báo trước tính theo ngày làm việc, không tính ngày nộp đơn, ngày nghỉ đầu tiên, ngày nghỉ cuối tuần và ngày nghỉ lễ. Ví dụ, nhân viên muốn nghỉ vào thứ Sáu cần gửi đơn chậm nhất vào thứ Ba của tuần đó. Nhân viên muốn nghỉ vào thứ Hai cần gửi đơn chậm nhất vào thứ Tư của tuần trước, vì thứ Bảy và Chủ nhật không được tính.",
    carry_txt="Phép năm không sử dụng hết được chuyển tối đa 5 ngày sang năm sau và hết hạn vào ngày 31/03 năm kế tiếp. Nhân viên có thể yêu cầu thanh toán bằng tiền cho số ngày phép còn lại.",
    carry_ex="Ví dụ. Cuối năm nhân viên còn 7 ngày phép chưa dùng. Nhân viên được chuyển 5 ngày sang năm sau và phải dùng hết trước ngày 31/03. Với 2 ngày còn lại, nhân viên có thể yêu cầu thanh toán bằng tiền hoặc không chuyển. Số ngày đã chuyển mà đến hết ngày 31/03 vẫn chưa dùng thì hết hạn, trừ khi nhân viên đã gửi yêu cầu thanh toán trước thời điểm đó.",
    carry_short="Tối đa 5 ngày, hết hạn ngày 31/03 năm kế tiếp",
    step_appr="Quản lý trực tiếp xem xét và phê duyệt đơn trên HR Portal. Nếu đơn nghỉ từ 5 ngày liên tục trở lên, trưởng phòng phê duyệt sau khi quản lý xác nhận.",
    balance_ex="Nhân viên có 10 năm thâm niên được 12 ngày phép cơ bản cộng thêm 2 ngày, tổng cộng 14 ngày. Trong năm, nhân viên nghỉ hai đợt: đợt đầu 3 ngày làm việc và đợt sau 4 ngày làm việc, tổng cộng đã dùng 7 ngày. Số dư cuối năm là 7 ngày. Nhân viên chuyển 5 ngày sang năm sau, phải dùng hết trước ngày 31/03, và yêu cầu thanh toán bằng tiền cho 2 ngày còn lại trước ngày 31/12.",
    faq=[
        "Hỏi: Nhân viên chính thức được nghỉ phép năm bao nhiêu ngày? Đáp: Mỗi nhân viên chính thức được hưởng 12 ngày phép năm có lương, chưa gồm số ngày cộng thêm theo thâm niên.",
        "Hỏi: Nhân viên có 10 năm thâm niên được bao nhiêu ngày phép? Đáp: Được 14 ngày phép, gồm 12 ngày cơ bản cộng thêm 2 ngày theo thâm niên.",
        "Hỏi: Tôi phải đăng ký nghỉ phép trước bao lâu và ở đâu? Đáp: Phép năm phải được đăng ký trước ít nhất 2 ngày làm việc qua HR Portal.",
        "Hỏi: Nghỉ phép 5 ngày liên tục thì ai phê duyệt? Đáp: Nghỉ phép từ 5 ngày liên tục trở lên cần trưởng phòng phê duyệt, sau khi quản lý trực tiếp xác nhận đã sắp xếp người thay thế.",
        "Hỏi: Nghỉ từ thứ Tư đến thứ Ba tuần sau có phải nghỉ dài cần trưởng phòng không? Đáp: Có. Kỳ nghỉ này gồm 5 ngày phép bị trừ (thứ Tư, thứ Năm, thứ Sáu, thứ Hai, thứ Ba), thứ Bảy và Chủ nhật nằm xen giữa không làm đứt tính liên tục nên đơn cần trưởng phòng phê duyệt.",
        "Hỏi: Phép năm không dùng hết thì chuyển được bao nhiêu ngày? Đáp: Được chuyển tối đa 5 ngày sang năm sau và hết hạn vào ngày 31/03 năm kế tiếp.",
        "Hỏi: Tôi có thể lấy tiền thay cho ngày phép còn lại không? Đáp: Có. Nhân viên có thể yêu cầu thanh toán bằng tiền cho số ngày phép còn lại qua HR Portal, đúng thời hạn nêu ở mục Thanh toán bằng tiền.",
        "Hỏi: Nhân viên thử việc có được nghỉ phép năm không? Đáp: Không. Nhân viên thử việc không được nghỉ phép năm, xem Chính sách thử việc.",
        "Hỏi: Tôi hủy đơn nghỉ phép được không? Đáp: Được. Nhân viên sửa hoặc hủy đơn trước ngày nghỉ ít nhất 1 ngày làm việc; số ngày phép được hoàn lại sau khi Phòng Nhân sự cập nhật.",
        "Hỏi: Kỳ nghỉ của tôi bắt đầu trước khi chính sách mới có hiệu lực nhưng kết thúc sau đó thì áp dụng bản nào? Đáp: Áp dụng phiên bản có hiệu lực tại ngày nghỉ đầu tiên của kỳ nghỉ.",
        "Hỏi: Nghỉ nửa ngày có được không? Đáp: Có. Nghỉ nửa ngày bị trừ 0,5 ngày phép.",
    ],
    history=[
        ["1.0", "01/01/2023", "Ban hành lần đầu chính sách nghỉ phép năm.", "Phòng Nhân sự"],
        ["2.0", "01/01/2024", "Tăng số ngày phép năm; rút ngắn thời hạn đăng ký trước; bổ sung quy định phê duyệt của trưởng phòng đối với kỳ nghỉ dài; tăng số ngày phép được chuyển sang năm sau và bổ sung thời hạn hết hạn; bổ sung quy định thanh toán bằng tiền và loại trừ nhân viên thử việc.", "Phòng Nhân sự"],
    ],
)

_CFG_C = dict(
    key="c", code="SYN-D03c", full=False, long_leave=True, cash=True,
    status="Chưa có hiệu lực (hiệu lực từ ngày 01/01/2027)",
    period="Từ ngày 01/01/2027 cho đến khi có phiên bản thay thế",
    ctrl_note="Đây là phiên bản 2027 của Chính sách nghỉ phép năm. Phiên bản này có hiệu lực từ ngày 01/01/2027 và chưa được áp dụng trước ngày đó; cho đến hết ngày 31/12/2026, nhân sự tiếp tục áp dụng phiên bản đang có hiệu lực tại thời điểm nghỉ.",
    effect_txt="Phiên bản này có hiệu lực từ ngày 01/01/2027 và thay thế phiên bản 2.0 kể từ ngày đó. Kỳ nghỉ bắt đầu trước ngày 01/01/2027 không áp dụng phiên bản này, kể cả khi ngày kết thúc kỳ nghỉ nằm sau ngày có hiệu lực. Số ngày phép chưa dùng của năm phép trước được xử lý theo quy định về chuyển phép của chính sách này.",
    base="13 ngày", adv="2 ngày làm việc",
    base_txt="Từ ngày 01/01/2027, mỗi nhân viên chính thức được hưởng 13 ngày phép năm có lương. Chính sách này thay thế phiên bản 2.0 kể từ ngày có hiệu lực.",
    pro_ex="Ví dụ 1. Nhân viên trở thành nhân viên chính thức từ ngày 01/07, còn 6 tháng trong năm phép. Số phép được hưởng bằng 13 ngày nhân 6 chia 12, tương đương 6,5 ngày phép. Ví dụ 2. Nhân viên trở thành nhân viên chính thức từ ngày 20/07, thuộc nửa sau tháng nên tính từ tháng 8, còn 5 tháng. Số phép bằng 13 ngày nhân 5 chia 12, làm tròn xuống thành 5 ngày phép.",
    sen_ex="Ví dụ. Nhân viên có 7 năm thâm niên đủ vào ngày 01/01 được cộng thêm 1 ngày phép vào mức cơ bản, tổng cộng 14 ngày phép năm. Nhân viên có 4 năm 11 tháng thâm niên chưa được cộng thêm ngày nào vì chưa đủ 5 năm.",
    reg_txt="Phép năm phải được đăng ký trước ít nhất 2 ngày làm việc qua HR Portal. Nghỉ từ 5 ngày liên tục trở lên cần trưởng phòng phê duyệt.",
    reg_extra="Đơn đăng ký nêu rõ ngày nghỉ, loại nghỉ và người thay thế. Thời hạn báo trước tính theo ngày làm việc, không tính ngày nộp đơn, ngày nghỉ đầu tiên, ngày nghỉ cuối tuần và ngày nghỉ lễ. Ví dụ, nhân viên muốn nghỉ vào thứ Sáu cần gửi đơn chậm nhất vào thứ Ba của tuần đó.",
    carry_txt="Phép năm không sử dụng hết được chuyển tối đa 5 ngày sang năm sau và hết hạn vào ngày 31/03 năm kế tiếp. Nhân viên có thể yêu cầu thanh toán bằng tiền cho số ngày phép còn lại.",
    carry_ex="Ví dụ. Cuối năm nhân viên còn 8 ngày phép chưa dùng. Nhân viên được chuyển 5 ngày sang năm sau và phải dùng hết trước ngày 31/03. Với 3 ngày còn lại, nhân viên có thể yêu cầu thanh toán bằng tiền hoặc không chuyển.",
    carry_short="Tối đa 5 ngày, hết hạn ngày 31/03 năm kế tiếp",
    step_appr="Quản lý trực tiếp xem xét và phê duyệt đơn trên HR Portal. Nếu đơn nghỉ từ 5 ngày liên tục trở lên, trưởng phòng phê duyệt sau khi quản lý xác nhận.",
    balance_ex="",
    faq=[
        "Hỏi: Từ năm 2027 nhân viên chính thức được nghỉ phép năm bao nhiêu ngày? Đáp: Từ ngày 01/01/2027, mỗi nhân viên chính thức được hưởng 13 ngày phép năm có lương, chưa gồm số ngày cộng thêm theo thâm niên.",
        "Hỏi: Phiên bản này áp dụng từ khi nào? Đáp: Từ ngày 01/01/2027. Trước ngày đó nhân sự tiếp tục áp dụng phiên bản đang có hiệu lực.",
        "Hỏi: Tôi phải đăng ký nghỉ phép trước bao lâu và ở đâu? Đáp: Phép năm phải được đăng ký trước ít nhất 2 ngày làm việc qua HR Portal.",
        "Hỏi: Nghỉ 5 ngày liên tục thì ai phê duyệt? Đáp: Nghỉ từ 5 ngày liên tục trở lên cần trưởng phòng phê duyệt.",
        "Hỏi: Nhân viên thử việc có được nghỉ phép năm không? Đáp: Không. Nhân viên thử việc không được nghỉ phép năm, xem Chính sách thử việc.",
        "Hỏi: Kỳ nghỉ bắt đầu vào ngày cuối của năm trước và kết thúc sau ngày 01/01/2027 áp dụng bản nào? Đáp: Áp dụng phiên bản có hiệu lực tại ngày nghỉ đầu tiên của kỳ nghỉ; phiên bản này không áp dụng cho kỳ nghỉ bắt đầu trước ngày 01/01/2027.",
        "Hỏi: Phép năm chưa dùng hết được chuyển thế nào? Đáp: Được chuyển tối đa 5 ngày sang năm sau và hết hạn vào ngày 31/03 năm kế tiếp.",
        "Hỏi: Tôi có thể lấy tiền thay cho ngày phép còn lại không? Đáp: Có, nhân viên có thể yêu cầu thanh toán bằng tiền cho số ngày phép còn lại qua HR Portal.",
    ],
    history=[
        ["1.0", "01/01/2023", "Ban hành lần đầu chính sách nghỉ phép năm.", "Phòng Nhân sự"],
        ["2.0", "01/01/2024", "Tăng số ngày phép năm; rút ngắn thời hạn đăng ký trước; bổ sung quy định phê duyệt của trưởng phòng đối với kỳ nghỉ dài; tăng số ngày phép được chuyển sang năm sau và bổ sung thời hạn hết hạn; bổ sung quy định thanh toán bằng tiền và loại trừ nhân viên thử việc.", "Phòng Nhân sự"],
        ["3.0", "01/01/2027", "Tăng số ngày phép năm áp dụng từ ngày phiên bản có hiệu lực; giữ cấu trúc và quy trình đăng ký như phiên bản đang áp dụng ngay trước đó.", "Phòng Nhân sự"],
    ],
)

D03a = _leave_doc(_CFG_A)
D03b = _leave_doc(_CFG_B)
D03c = _leave_doc(_CFG_C)

QA_D03 = [
    # ---- D03a
    {"id": "L-D03a-1", "q": "Theo chính sách nghỉ phép năm 2023, nếu cuối năm còn 4 ngày phép chưa dùng thì được chuyển mấy ngày sang năm sau?", "must_include": ["chuyển tối đa 3 ngày"], "docs": ["D03a"], "as_of": "2023-06-01"},
    {"id": "L-D03a-2", "q": "Nhân viên thành chính thức từ ngày 01/07 thì phép năm 2023 được tính bao nhiêu ngày?", "must_include": ["tương đương 5 ngày phép"], "docs": ["D03a"], "as_of": "2023-06-01"},
    {"id": "L-D03a-3", "q": "Muốn nghỉ vào thứ Sáu theo chính sách nghỉ phép 2023 thì phải gửi đơn chậm nhất khi nào?", "must_include": ["chậm nhất vào thứ Hai của tuần đó"], "docs": ["D03a"], "as_of": "2023-06-01"},
    {"id": "L-D03a-4", "q": "Ai phê duyệt mọi đơn nghỉ phép năm theo chính sách 2023?", "must_include": ["Quản lý trực tiếp phê duyệt mọi đơn nghỉ phép"], "docs": ["D03a"], "as_of": "2023-06-01"},
    # ---- D03b
    {"id": "L-D03b-1", "q": "Nghỉ từ thứ Tư đến thứ Ba tuần sau có tính là nghỉ liên tục từ 5 ngày cần trưởng phòng phê duyệt không?", "must_include": ["không làm đứt tính liên tục"], "docs": ["D03b"]},
    {"id": "L-D03b-2", "q": "Nhân viên còn 7 ngày phép cuối năm thì xử lý thế nào và hạn yêu cầu thanh toán bằng tiền là khi nào?", "must_include": ["chậm nhất vào ngày 31/12", "chậm nhất vào ngày 31/03"], "docs": ["D03b"]},
    {"id": "L-D03b-3", "q": "Trưởng phòng phải phản hồi đơn nghỉ dài trong bao lâu?", "must_include": ["Trong 2 ngày làm việc kể từ khi quản lý xác nhận"], "docs": ["D03b"]},
    {"id": "L-D03b-4", "q": "Nếu nhân viên tách một kỳ nghỉ dài thành nhiều đơn ngắn liền nhau thì xử lý thế nào?", "must_include": ["các đơn đó được gộp lại để xác định cấp phê duyệt"], "docs": ["D03b"]},
    {"id": "L-D03b-5", "q": "Kỳ nghỉ bắt đầu trước ngày chuyển đổi chính sách nhưng kết thúc sau đó thì áp dụng phiên bản nào?", "must_include": ["ngày nghỉ đầu tiên của kỳ nghỉ"], "docs": ["D03b"]},
    # ---- D03c
    {"id": "L-D03c-1", "q": "Nhân viên thành chính thức từ ngày 01/07/2027 thì phép năm được tính bao nhiêu ngày?", "must_include": ["tương đương 6,5 ngày phép"], "docs": ["D03c"], "as_of": "2027-02-01"},
    {"id": "L-D03c-2", "q": "Kỳ nghỉ bắt đầu trước ngày 01/01/2027 nhưng kết thúc sau đó có áp dụng chính sách phiên bản 2027 không?", "must_include": ["Kỳ nghỉ bắt đầu trước ngày 01/01/2027 không áp dụng phiên bản này"], "docs": ["D03c"], "as_of": "2027-02-01"},
    {"id": "L-D03c-3", "q": "Nhân viên có 7 năm thâm niên theo chính sách nghỉ phép năm 2027 được cộng thêm bao nhiêu ngày phép?", "must_include": ["được cộng thêm 1 ngày phép vào mức cơ bản"], "docs": ["D03c"], "as_of": "2027-02-01"},
    {"id": "L-D03c-4", "q": "Cuối năm còn 8 ngày phép chưa dùng thì chuyển tối đa mấy ngày theo chính sách 2027?", "must_include": ["Nhân viên được chuyển 5 ngày sang năm sau"], "docs": ["D03c"], "as_of": "2027-02-01"},
]

# =====================================================================================================
# D04 - Chính sách thử việc
# =====================================================================================================
D04 = [
    H1("Thông tin kiểm soát tài liệu"),
    ctrl("SYN-D04", "Giám đốc Nhân sự",
         "Nhân viên thử việc; quản lý trực tiếp và trưởng phòng có nhân viên thử việc; Phòng Nhân sự", "Đang hiệu lực"),
    P("Chính sách thử việc là căn cứ để nhân sự mới biết mình được hưởng gì và bị đánh giá thế nào trong những tuần đầu, đồng thời giúp quản lý thực hiện đánh giá thống nhất. Bản in hoặc bản sao ngoài kho tài liệu nội bộ không còn được kiểm soát; khi cần đối chiếu, luôn dùng phiên bản đang hiển thị trên kho tài liệu."),

    H1("Mục đích và phạm vi"),
    H2("Mục đích"),
    P("Chính sách này quy định thời gian thử việc, mức lương thử việc, quyền lợi trong thời gian thử việc, lịch và cách thức đánh giá thử việc, cũng như cách công ty và nhân sự kết thúc giai đoạn thử việc. Mục tiêu là để hai bên có đủ thời gian và căn cứ rõ ràng để quyết định việc làm việc lâu dài, đồng thời bảo đảm nhân sự mới được hỗ trợ đầy đủ ngay từ ngày đầu."),
    H2("Phạm vi và đối tượng áp dụng"),
    P("Chính sách áp dụng cho mọi nhân sự ký hợp đồng thử việc hoặc có điều khoản thử việc trong hợp đồng lao động với công ty, tại tất cả các văn phòng. Thực tập sinh không thuộc phạm vi chính sách này và thời gian làm thực tập không được tính vào thời gian thử việc. Quản lý trực tiếp, trưởng phòng và Phòng Nhân sự áp dụng chính sách này khi hướng dẫn, đánh giá và ra quyết định về nhân viên thử việc."),
    H2("Căn cứ và tài liệu liên quan"),
    B("Bộ luật Lao động 2019 (45/2019/QH14): quy định pháp luật về hợp đồng lao động và thử việc.",
      "Nội quy lao động: giờ làm việc, ứng xử và xử lý vi phạm, áp dụng cho cả nhân viên thử việc.",
      "Chính sách nghỉ phép năm: quy định phép năm dành cho nhân viên chính thức.",
      "Chính sách phúc lợi và bảo hiểm: các khoản phúc lợi và đối tượng hưởng.",
      "Bảng phụ cấp theo cấp bậc: các khoản phụ cấp hằng tháng theo cấp bậc.",
      "Chính sách làm việc từ xa: điều kiện làm việc từ xa ngoài thứ Bảy.",
      "Chương trình Mentor và Buddy: hỗ trợ nhân sự mới trong những tháng đầu.",
      "Hướng dẫn ngày đầu đi làm: thủ tục tiếp nhận và lịch trong ngày đầu tiên."),

    H1("Định nghĩa và thuật ngữ"),
    T(["Thuật ngữ", "Định nghĩa dùng trong chính sách này"], [
        ["Thử việc", "Giai đoạn đầu của quan hệ lao động, trong đó hai bên đánh giá mức độ phù hợp trước khi ký hợp đồng lao động chính thức."],
        ["Ngày bắt đầu làm việc", "Ngày nhân sự có mặt làm việc theo thư mời nhận việc; được tính là ngày thứ 1 của thời gian thử việc."],
        ["Ngày thứ N", "Số thứ tự của ngày theo lịch kể từ ngày bắt đầu làm việc, gồm cả ngày nghỉ cuối tuần và ngày nghỉ lễ. Ví dụ ngày thứ 30 là ngày thứ ba mươi kể từ ngày bắt đầu làm việc."],
        ["Ngày làm việc", "Các ngày từ thứ Hai đến thứ Sáu, không kể ngày nghỉ lễ theo lịch công ty công bố."],
        ["Vị trí quản lý cấp cao", "Vị trí từ cấp bậc Manager trở lên."],
        ["Mức lương của cấp bậc tương ứng", "Mức lương chính thức theo cấp bậc của vị trí được ghi trong thư mời nhận việc, chưa nhân với tỷ lệ thử việc."],
        ["Đánh giá giữa kỳ", "Buổi đánh giá do quản lý trực tiếp thực hiện vào ngày thứ 30."],
        ["Đánh giá cuối kỳ", "Buổi đánh giá do quản lý trực tiếp thực hiện vào ngày thứ 55, làm căn cứ quyết định ký hợp đồng chính thức."],
        ["Nghỉ không lương", "Ngày nghỉ được phê duyệt trong đó nhân sự không được trả lương."],
        ["Quản lý trực tiếp", "Người quản lý công việc hằng ngày và thực hiện đánh giá nhân viên thử việc."],
        ["Trưởng phòng", "Người đứng đầu đơn vị, phê duyệt nghỉ không lương và xác nhận kết quả đánh giá cuối kỳ."],
        ["HR Portal", "Cổng thông tin nhân sự nội bộ, nơi ghi nhận đề nghị nghỉ, biên bản đánh giá và kết quả."],
    ], widths=[3.5, 8.5]),

    H1("Vai trò và trách nhiệm"),
    T(["Vai trò", "Trách nhiệm chính", "Ghi chú"], [
        ["Nhân viên thử việc", "Hoàn thành mục tiêu đã thống nhất, tuân thủ nội quy, chủ động xin phản hồi.", "Chịu trách nhiệm chính về kết quả công việc."],
        ["Quản lý trực tiếp", "Thống nhất mục tiêu, hướng dẫn, đánh giá vào ngày thứ 30 và ngày thứ 55, đề xuất kết quả.", "Không chuyển giao việc đánh giá cho người khác."],
        ["Trưởng phòng", "Phê duyệt nghỉ không lương, xác nhận kết quả đánh giá cuối kỳ.", "Có thể xem xét lại khi có khiếu nại."],
        ["Phòng Nhân sự", "Sở hữu chính sách, lưu biên bản, thông báo kết quả, làm hợp đồng chính thức.", "Đầu mối HR Onboarding."],
        ["Buddy và Mentor", "Hỗ trợ hòa nhập và chuyên môn theo Chương trình Mentor và Buddy.", "Không phải người đánh giá thử việc."],
        ["Khối Công nghệ thông tin (giả định)", "Cấp và thu hồi tài khoản, thiết bị theo tình trạng thử việc.", "Liên hệ qua IT Helpdesk."],
    ], widths=[3, 6.5, 3.5]),

    H1("Thời gian thử việc"),
    H2("Thời gian thử việc tiêu chuẩn"),
    P("Thời gian thử việc tiêu chuẩn là 60 ngày kể từ ngày bắt đầu làm việc. Với vị trí quản lý cấp cao (Manager trở lên), thời gian thử việc có thể kéo dài đến 90 ngày."),
    P("Thời gian thử việc cụ thể của từng người được ghi trong thư mời nhận việc và hợp đồng thử việc, do Phòng Nhân sự xác nhận trước ngày bắt đầu làm việc. Ngày bắt đầu làm việc được tính là ngày thứ 1, và ngày kết thúc thử việc là ngày cuối cùng của khoảng thời gian đã ghi, gồm cả ngày nghỉ cuối tuần và ngày nghỉ lễ nằm trong khoảng đó."),
    H2("Vị trí quản lý cấp cao"),
    P("Mức thử việc đến 90 ngày chỉ áp dụng cho vị trí Manager trở lên, vì các vị trí này cần thêm thời gian để đánh giá năng lực quản lý và kết quả dẫn dắt đội. Thời gian này là mức tối đa, không phải mức mặc định; Phòng Nhân sự và Trưởng phòng quyết định thời gian cụ thể trong thư mời nhận việc. Vị trí dưới Manager không được kéo dài quá mức tiêu chuẩn."),
    H2("Không gia hạn ngoài mức quy định"),
    P("Công ty không gia hạn thời gian thử việc vượt quá mức tối đa nêu trên, dù kết quả đánh giá chưa rõ ràng. Nếu đến cuối thời gian thử việc mà quản lý vẫn chưa đủ căn cứ, quản lý phải đưa ra kết luận đạt hoặc không đạt dựa trên các dữ liệu đã ghi nhận, không dùng việc kéo dài thử việc để thay cho quyết định."),
    H2("Ví dụ về lịch thử việc"),
    P("Ví dụ. Nhân sự bắt đầu làm việc vào thứ Hai, ngày 02/06/2025. Ngày này là ngày thứ 1. Ngày thứ 30 là thứ Ba, ngày 01/07/2025; ngày thứ 55 là thứ Bảy, ngày 26/07/2025; ngày thứ 60 là thứ Năm, ngày 31/07/2025 và là ngày kết thúc thử việc tiêu chuẩn. Hợp đồng lao động chính thức, nếu đạt, có hiệu lực từ ngày làm việc kế tiếp là thứ Sáu, ngày 01/08/2025."),

    H1("Lương thử việc"),
    P("Nhân viên thử việc được nhận 85% mức lương của cấp bậc tương ứng. Phụ cấp ăn trưa được áp dụng đầy đủ từ ngày đầu tiên."),
    P("Cách tính rất đơn giản: lương thử việc bằng 85% mức lương của cấp bậc tương ứng nhân với tỷ lệ ngày công thực tế trong tháng. Ví dụ minh họa, nếu mức lương của cấp bậc tương ứng là X thì lương thử việc theo tháng đầy đủ là 0,85 nhân X. Sau khi ký hợp đồng chính thức, lương được trả 100% mức lương của cấp bậc tương ứng kể từ ngày hợp đồng chính thức có hiệu lực."),
    P("Lương thử việc được trả trong kỳ trả lương chung của công ty, sau khi khấu trừ các khoản theo quy định của pháp luật. Phụ cấp ăn trưa được áp dụng đầy đủ từ ngày đầu tiên và không bị giảm theo tỷ lệ 85%; mức cụ thể xem Chính sách phúc lợi và bảo hiểm. Việc áp dụng các phụ cấp khác trong thời gian thử việc được ghi trong thư mời nhận việc; chính sách này chỉ quy định về phụ cấp ăn trưa."),
    P("Thông tin lương cá nhân thuộc cấp phân loại Bí mật. Nhân sự không trao đổi mức lương thử việc của mình hoặc của người khác qua kênh công khai; thắc mắc về lương gửi Phòng Nhân sự qua HR Portal."),

    H1("Quyền lợi trong thời gian thử việc"),
    H2("Nghỉ phép và nghỉ không lương"),
    P("Nhân viên thử việc không được nghỉ phép năm. Trường hợp cần nghỉ việc riêng, nhân viên thử việc xin nghỉ không lương và được trưởng phòng phê duyệt."),
    P("Ngày nghỉ lễ theo lịch nghỉ lễ do công ty công bố vẫn áp dụng cho nhân viên thử việc đang làm việc tại công ty. Nghỉ không lương không làm thay đổi ngày kết thúc thử việc và không làm thay đổi ngày đánh giá theo lịch. Nếu tổng số ngày nghỉ không lương dài đến mức không đủ dữ liệu để đánh giá, quản lý báo Phòng Nhân sự để xem xét việc bổ sung một buổi đánh giá trước khi quyết định."),
    N("Trao đổi với quản lý trực tiếp về lý do và thời gian dự kiến nghỉ, càng sớm càng tốt; trường hợp đột xuất báo ngay trong ngày.",
      "Gửi đề nghị nghỉ không lương trên HR Portal, nêu ngày bắt đầu, ngày kết thúc và lý do.",
      "Quản lý trực tiếp xác nhận việc nghỉ không ảnh hưởng đến kế hoạch công việc và chuyển đề nghị lên trưởng phòng.",
      "Trưởng phòng xem xét và phê duyệt hoặc từ chối trên HR Portal; nếu từ chối, nêu lý do.",
      "Phòng Nhân sự ghi nhận ngày nghỉ không lương để không tính lương cho những ngày này."),
    H2("Bảo hiểm"),
    P("Nhân viên thử việc được tham gia bảo hiểm xã hội bắt buộc nhưng chưa được hưởng gói bảo hiểm sức khỏe PVI."),
    P("Gói bảo hiểm sức khỏe PVI được cấp cho nhân viên chính thức, vì vậy quyền lợi này bắt đầu sau khi nhân sự ký hợp đồng lao động chính thức. Thời gian thử việc vẫn được tính vào thâm niên của nhân sự theo hướng dẫn của Phòng Nhân sự."),
    H2("Bảng tổng hợp quyền lợi"),
    T(["Quyền lợi", "Trong thời gian thử việc", "Ghi chú"], [
        ["Lương", "85% mức lương của cấp bậc tương ứng", "Sau thử việc là 100%"],
        ["Phụ cấp ăn trưa", "Áp dụng đầy đủ từ ngày đầu tiên", "Không giảm theo tỷ lệ thử việc"],
        ["Nghỉ phép năm", "Không được nghỉ phép năm", "Nghỉ việc riêng xin nghỉ không lương"],
        ["Bảo hiểm xã hội bắt buộc", "Có", "Theo quy định pháp luật"],
        ["Bảo hiểm sức khỏe PVI", "Chưa được hưởng", "Bắt đầu sau khi ký hợp đồng chính thức"],
        ["Làm việc từ xa ngày khác", "Không áp dụng", "Thứ Bảy làm việc từ xa theo phân công vẫn thực hiện theo Nội quy lao động"],
        ["Hỗ trợ Buddy và Mentor", "Có", "Theo Chương trình Mentor và Buddy"],
    ], widths=[3.5, 4.5, 4]),
    H2("Hỗ trợ hòa nhập"),
    P("Nhân sự mới được hỗ trợ theo Chương trình Mentor và Buddy ngay từ những ngày đầu. Buddy hỗ trợ hòa nhập trong 3 tháng đầu và Mentor đồng hành chuyên môn trong 6 tháng đầu; thời gian hỗ trợ trải dài cả thời gian thử việc và một phần thời gian sau đó. Quản lý trực tiếp không đóng vai trò Mentor hoặc Buddy, vì vậy nhân viên thử việc có thể trao đổi thẳng thắn với người hỗ trợ về khó khăn mà không lo ảnh hưởng đến đánh giá."),

    H1("Đánh giá thử việc"),
    P("Quản lý trực tiếp thực hiện đánh giá vào ngày thứ 30 (giữa kỳ) và ngày thứ 55 (cuối kỳ). Kết quả đánh giá quyết định việc ký hợp đồng chính thức."),
    H2("Đánh giá giữa kỳ vào ngày thứ 30"),
    P("Buổi đánh giá giữa kỳ là buổi trao đổi một đối một giữa quản lý trực tiếp và nhân viên thử việc. Quản lý nêu điểm mạnh, điểm cần cải thiện dựa trên các mục tiêu đã thống nhất, đồng thời lắng nghe khó khăn của nhân viên. Kết quả giữa kỳ được xếp loại Đúng hướng hoặc Cần cải thiện và ghi nhận trên HR Portal trong 2 ngày làm việc kể từ ngày đánh giá thực tế. Nếu kết quả là Cần cải thiện, quản lý và nhân viên thống nhất hành động cụ thể cho giai đoạn còn lại."),
    H2("Đánh giá cuối kỳ vào ngày thứ 55"),
    P("Đánh giá cuối kỳ tổng hợp toàn bộ quá trình thử việc và làm căn cứ quyết định ký hợp đồng chính thức. Quản lý lập biên bản đánh giá cuối kỳ, đề xuất kết quả Đạt hoặc Không đạt và gửi Trưởng phòng cùng Phòng Nhân sự trong 2 ngày làm việc kể từ ngày đánh giá thực tế. Trưởng phòng xác nhận kết quả trong 1 ngày làm việc kể từ khi nhận biên bản. Phòng Nhân sự thông báo kết quả chính thức cho nhân sự trước ngày kết thúc thử việc."),
    H2("Khi ngày đánh giá rơi vào ngày nghỉ"),
    P("Nếu ngày thứ 30 hoặc ngày thứ 55 rơi vào thứ Bảy, Chủ nhật hoặc ngày nghỉ lễ, quản lý thực hiện đánh giá vào ngày làm việc liền trước. Trường hợp ngày làm việc liền trước nằm trước ngày bắt đầu làm việc thì đánh giá vào ngày làm việc đầu tiên sau đó. Trong ví dụ ở mục Thời gian thử việc, ngày thứ 55 là thứ Bảy nên buổi đánh giá cuối kỳ diễn ra vào thứ Sáu, ngày 25/07/2025."),
    H2("Tiêu chí đánh giá"),
    T(["Nhóm tiêu chí", "Nội dung xem xét", "Nguồn dữ liệu"], [
        ["Kết quả công việc", "Mức độ hoàn thành mục tiêu đã thống nhất trong tháng đầu và cuối kỳ", "Sản phẩm, báo cáo, phản hồi của đội"],
        ["Năng lực chuyên môn", "Khả năng học nhanh, áp dụng kiến thức và giải quyết vấn đề", "Quan sát của quản lý, đầu ra công việc"],
        ["Tuân thủ nội quy", "Giờ giấc, bảo mật thông tin, trang phục, ứng xử", "Ghi nhận trên HR Portal"],
        ["Hòa nhập và hợp tác", "Cách phối hợp với đồng nghiệp, tiếp nhận phản hồi", "Trao đổi với Buddy và đồng nghiệp"],
        ["Thái độ và tinh thần trách nhiệm", "Chủ động, trung thực, dám nhận việc", "Quan sát của quản lý"],
    ], widths=[3, 5.5, 3.5]),
    H2("Kết quả và quyết định"),
    T(["Kết quả cuối kỳ", "Ý nghĩa", "Bước tiếp theo"], [
        ["Đạt", "Đáp ứng yêu cầu của vị trí", "Ký hợp đồng lao động chính thức"],
        ["Không đạt", "Chưa đáp ứng yêu cầu của vị trí sau khi đã được hỗ trợ và phản hồi", "Chấm dứt thử việc theo quy định pháp luật và hợp đồng thử việc"],
    ], widths=[3, 5.5, 3.5]),
    P("Kết quả Không đạt phải có căn cứ cụ thể, dựa trên các biên bản đánh giá và dữ liệu công việc đã ghi nhận, và được trao đổi trực tiếp với nhân viên trước khi thông báo chính thức. Công ty không đưa ra kết quả Không đạt chỉ dựa trên một sự việc đơn lẻ nếu chưa có phản hồi hoặc cơ hội cải thiện."),
    H2("Vị trí thử việc đến 90 ngày"),
    P("Với vị trí quản lý cấp cao thử việc đến 90 ngày, buổi đánh giá vào ngày thứ 30 và ngày thứ 55 vẫn được thực hiện theo lịch chung, đóng vai trò các mốc theo dõi tiến độ. Phòng Nhân sự và quản lý thống nhất thêm một buổi rà soát trước khi chốt quyết định ký hợp đồng chính thức; thời điểm buổi rà soát này được ghi trong kế hoạch thử việc của vị trí."),
    H2("Lịch mốc thời gian"),
    T(["Mốc", "Việc phải làm", "Thời hạn", "Bên thực hiện"], [
        ["Trước ngày bắt đầu", "Xác nhận thời gian thử việc trong thư mời nhận việc", "Trước ngày bắt đầu làm việc", "Phòng Nhân sự"],
        ["Tuần đầu", "Thống nhất mục tiêu thử việc", "Trong tuần làm việc đầu tiên", "Quản lý và nhân viên"],
        ["Ngày thứ 30", "Đánh giá giữa kỳ", "Ngày thứ 30, hoặc ngày làm việc liền trước", "Quản lý trực tiếp"],
        ["Sau ngày thứ 30", "Ghi nhận kết quả giữa kỳ", "Trong 2 ngày làm việc", "Quản lý trực tiếp"],
        ["Ngày thứ 55", "Đánh giá cuối kỳ", "Ngày thứ 55, hoặc ngày làm việc liền trước", "Quản lý trực tiếp"],
        ["Sau ngày thứ 55", "Gửi đề xuất cho Trưởng phòng và Phòng Nhân sự", "Trong 2 ngày làm việc", "Quản lý trực tiếp"],
        ["Sau khi nhận biên bản", "Xác nhận kết quả", "Trong 1 ngày làm việc", "Trưởng phòng"],
        ["Trước ngày kết thúc", "Thông báo kết quả chính thức", "Trước ngày kết thúc thử việc", "Phòng Nhân sự"],
    ], widths=[2.5, 4, 3.5, 2.5]),

    H1("Quy trình thử việc từng bước"),
    N("Trước ngày bắt đầu làm việc, Phòng Nhân sự gửi thư mời nhận việc ghi rõ thời gian thử việc, cấp bậc và tỷ lệ lương thử việc.",
      "Ngày đầu tiên, nhân sự hoàn tất thủ tục tiếp nhận, nhận thẻ từ và thiết bị theo Hướng dẫn ngày đầu đi làm; Buddy và Mentor được giới thiệu theo Chương trình Mentor và Buddy.",
      "Trong tuần đầu, quản lý trực tiếp và nhân viên thống nhất mục tiêu thử việc và cách đo kết quả, ghi nhận trên HR Portal.",
      "Thường xuyên trao đổi ngắn hằng tuần để nhân viên nhận phản hồi sớm và điều chỉnh kịp thời.",
      "Vào ngày thứ 30, quản lý thực hiện đánh giá giữa kỳ và ghi nhận kết quả trên HR Portal.",
      "Vào ngày thứ 55, quản lý thực hiện đánh giá cuối kỳ, lập biên bản và gửi đề xuất cho Trưởng phòng và Phòng Nhân sự.",
      "Trưởng phòng xác nhận kết quả; Phòng Nhân sự thông báo kết quả chính thức cho nhân sự trước ngày kết thúc thử việc.",
      "Nếu Đạt, Phòng Nhân sự chuẩn bị hợp đồng lao động chính thức, có hiệu lực từ ngày làm việc kế tiếp sau ngày kết thúc thử việc; nếu Không đạt, thực hiện các bước ở mục Kết thúc thử việc."),

    H1("Kết thúc thử việc"),
    H2("Trường hợp Đạt"),
    P("Khi kết quả là Đạt, nhân sự ký hợp đồng lao động chính thức và trở thành nhân viên chính thức từ ngày hợp đồng có hiệu lực. Từ thời điểm đó, nhân sự được hưởng 100% mức lương của cấp bậc tương ứng, được tham gia gói bảo hiểm sức khỏe PVI theo Chính sách phúc lợi và bảo hiểm, và được hưởng phép năm theo Chính sách nghỉ phép năm có hiệu lực tại thời điểm đó."),
    H2("Trường hợp Không đạt hoặc tự nguyện chấm dứt"),
    P("Khi kết quả là Không đạt hoặc khi nhân sự chủ động chấm dứt thử việc, hai bên thực hiện theo quy định của pháp luật lao động và hợp đồng thử việc. Trong thời gian bàn giao, nhân sự trả lại thiết bị, thẻ từ và thẻ xe (nếu có), bàn giao công việc và tài liệu cho quản lý trực tiếp. IT Helpdesk thu hồi thiết bị và khóa tài khoản theo yêu cầu của Phòng Nhân sự; Facilities thu hồi thẻ từ. Nhân sự vẫn phải tuân thủ nghĩa vụ bảo mật thông tin sau khi rời công ty."),
    H2("Khiếu nại kết quả đánh giá"),
    P("Nhân sự không đồng ý với kết quả đánh giá cuối kỳ có thể gửi ý kiến bằng văn bản tới hr-onboarding@vsf-demo.example hoặc qua HR Portal trong 3 ngày làm việc kể từ ngày nhận thông báo, nêu rõ nội dung không đồng ý và bằng chứng kèm theo. Phòng Nhân sự phối hợp với Trưởng phòng xem xét lại và phản hồi trong 5 ngày làm việc kể từ ngày nhận đủ thông tin. Việc xem xét lại không làm thay đổi ngày kết thúc thử việc đã ghi trong hợp đồng."),

    H1("Câu hỏi thường gặp"),
    P("Hỏi: Thời gian thử việc là bao lâu? Đáp: Thời gian thử việc tiêu chuẩn là 60 ngày kể từ ngày bắt đầu làm việc. Vị trí Manager trở lên có thể thử việc đến 90 ngày."),
    P("Hỏi: Lương thử việc bằng bao nhiêu phần trăm? Đáp: Nhân viên thử việc được nhận 85% mức lương của cấp bậc tương ứng. Phụ cấp ăn trưa được áp dụng đầy đủ từ ngày đầu tiên."),
    P("Hỏi: Nhân viên thử việc có được nghỉ phép năm không? Đáp: Không. Nhân viên thử việc không được nghỉ phép năm. Khi cần nghỉ việc riêng, bạn xin nghỉ không lương và được trưởng phòng phê duyệt."),
    P("Hỏi: Tôi có được hưởng bảo hiểm sức khỏe PVI khi đang thử việc không? Đáp: Chưa. Nhân viên thử việc được tham gia bảo hiểm xã hội bắt buộc nhưng chưa được hưởng gói bảo hiểm sức khỏe PVI, gói này bắt đầu sau khi ký hợp đồng chính thức."),
    P("Hỏi: Khi nào tôi được đánh giá? Đáp: Quản lý trực tiếp đánh giá vào ngày thứ 30 (giữa kỳ) và ngày thứ 55 (cuối kỳ). Kết quả đánh giá quyết định việc ký hợp đồng chính thức."),
    P("Hỏi: Nếu ngày thứ 55 rơi vào thứ Bảy thì đánh giá vào lúc nào? Đáp: Quản lý thực hiện đánh giá vào ngày làm việc liền trước, thường là thứ Sáu."),
    P("Hỏi: Sau đánh giá cuối kỳ, khi nào tôi biết kết quả? Đáp: Quản lý gửi đề xuất trong 2 ngày làm việc, Trưởng phòng xác nhận trong 1 ngày làm việc và Phòng Nhân sự thông báo kết quả chính thức trước ngày kết thúc thử việc."),
    P("Hỏi: Tôi xin nghỉ không lương thì cần làm gì? Đáp: Gửi đề nghị trên HR Portal, quản lý trực tiếp xác nhận và trưởng phòng phê duyệt. Ngày nghỉ không lương không được trả lương và không làm thay đổi ngày đánh giá theo lịch."),
    P("Hỏi: Thời gian thử việc có bị kéo dài nếu tôi chưa được đánh giá tốt không? Đáp: Không. Công ty không gia hạn thử việc vượt mức tối đa; quản lý phải đưa ra kết luận Đạt hoặc Không đạt dựa trên dữ liệu đã ghi nhận."),
    P("Hỏi: Tôi không đồng ý với kết quả Không đạt thì làm gì? Đáp: Gửi ý kiến bằng văn bản tới Phòng Nhân sự trong 3 ngày làm việc kể từ ngày nhận thông báo; Phòng Nhân sự phản hồi trong 5 ngày làm việc kể từ ngày nhận đủ thông tin."),
    P("Hỏi: Tôi có được làm việc từ xa vào ngày thường khi đang thử việc không? Đáp: Không, chính sách làm việc từ xa vào các ngày khác không áp dụng cho nhân viên thử việc. Thứ Bảy làm việc từ xa theo phân công của quản lý vẫn thực hiện theo Nội quy lao động."),

    H1("Phụ lục"),
    H2("Phụ lục A. Mẫu thông báo kết quả thử việc"),
    P("Nội dung mẫu Phòng Nhân sự gửi nhân sự sau khi Trưởng phòng xác nhận: 'Kính gửi bạn, căn cứ biên bản đánh giá cuối kỳ và Chính sách thử việc, kết quả thử việc của bạn là [Đạt hoặc Không đạt]. Thời gian thử việc kết thúc vào ngày [ngày kết thúc]. Nếu kết quả là Đạt, hợp đồng lao động chính thức có hiệu lực từ ngày [ngày hiệu lực]. Nếu bạn có ý kiến, vui lòng phản hồi trong 3 ngày làm việc kể từ ngày nhận thông báo.'"),
    H2("Phụ lục B. Danh sách kiểm tra dành cho quản lý trực tiếp"),
    B("Đã xác nhận với Phòng Nhân sự thời gian thử việc và cấp bậc của nhân viên.",
      "Đã thống nhất mục tiêu thử việc với nhân viên trong tuần đầu và ghi nhận trên HR Portal.",
      "Đã tính ngày thứ 30 và ngày thứ 55, đã đặt lịch đánh giá và tính đến trường hợp ngày đó rơi vào ngày nghỉ.",
      "Đã trao đổi phản hồi định kỳ với nhân viên, không để nhân viên bất ngờ với kết quả.",
      "Đã gửi biên bản cuối kỳ cho Trưởng phòng và Phòng Nhân sự trong 2 ngày làm việc.",
      "Đã đề nghị thu hồi thiết bị và tài khoản nếu kết quả là Không đạt."),
    H2("Phụ lục C. Mẫu ghi nhận đánh giá"),
    T(["Mục", "Đánh giá giữa kỳ (ngày thứ 30)", "Đánh giá cuối kỳ (ngày thứ 55)"], [
        ["Kết quả công việc", "Nhận xét ngắn và mức độ hoàn thành", "Nhận xét tổng hợp"],
        ["Điểm mạnh", "Nêu tối đa 3 điểm", "Nêu tối đa 3 điểm"],
        ["Điểm cần cải thiện", "Kèm hành động cụ thể", "Kèm đánh giá mức độ cải thiện"],
        ["Kết luận", "Đúng hướng hoặc Cần cải thiện", "Đạt hoặc Không đạt"],
        ["Ký nhận", "Quản lý và nhân viên", "Quản lý, Trưởng phòng, nhân viên"],
    ], widths=[3, 4.5, 4.5]),
    H2("Phụ lục D. Bảng tra cứu nhanh"),
    T(["Nội dung", "Quy định"], [
        ["Thời gian thử việc tiêu chuẩn", "60 ngày kể từ ngày bắt đầu làm việc"],
        ["Vị trí Manager trở lên", "Có thể thử việc đến 90 ngày"],
        ["Lương thử việc", "85% mức lương của cấp bậc tương ứng"],
        ["Phụ cấp ăn trưa", "Áp dụng đầy đủ từ ngày đầu tiên"],
        ["Nghỉ phép năm", "Không được nghỉ phép năm; nghỉ việc riêng xin nghỉ không lương"],
        ["Bảo hiểm", "Có bảo hiểm xã hội bắt buộc; chưa có bảo hiểm sức khỏe PVI"],
        ["Đánh giá", "Ngày thứ 30 (giữa kỳ) và ngày thứ 55 (cuối kỳ)"],
    ], widths=[4, 8]),

    H1("Lịch sử sửa đổi"),
    T(["Phiên bản", "Ngày", "Nội dung thay đổi", "Người soạn"], [
        ["1.0", "01/03/2023", "Ban hành lần đầu chính sách thử việc, nêu thời gian thử việc và lương thử việc.", "Phòng Nhân sự"],
        ["1.1", "01/09/2023", "Bổ sung quy định về quyền lợi trong thời gian thử việc và về đánh giá thử việc.", "Phòng Nhân sự"],
        ["1.2", "01/01/2024", "Bổ sung thời gian thử việc dài hơn cho vị trí quản lý cấp cao; làm rõ mốc đánh giá giữa kỳ và cuối kỳ; bổ sung ví dụ, lịch mốc thời gian, quy trình từng bước, khiếu nại và câu hỏi thường gặp.", "Phòng Nhân sự"],
    ], widths=[1.8, 2.2, 6.5, 2.5]),
]

QA_D04 = [
    {"id": "L-D04-1", "q": "Nếu ngày thứ 55 của thời gian thử việc rơi vào thứ Bảy thì quản lý đánh giá cuối kỳ vào ngày nào?", "must_include": ["ngày làm việc liền trước"], "docs": ["D04"]},
    {"id": "L-D04-2", "q": "Sau buổi đánh giá cuối kỳ, quản lý phải gửi đề xuất cho Trưởng phòng và Phòng Nhân sự trong bao lâu?", "must_include": ["trong 2 ngày làm việc kể từ ngày đánh giá thực tế"], "docs": ["D04"]},
    {"id": "L-D04-3", "q": "Vị trí Manager thử việc 90 ngày có còn đánh giá vào ngày thứ 30 và ngày thứ 55 không?", "must_include": ["vẫn được thực hiện theo lịch chung"], "docs": ["D04"]},
    {"id": "L-D04-4", "q": "Nhân viên thử việc không đồng ý với kết quả Không đạt có bao lâu để gửi ý kiến và Phòng Nhân sự phản hồi trong bao lâu?", "must_include": ["trong 3 ngày làm việc kể từ ngày nhận thông báo", "phản hồi trong 5 ngày làm việc"], "docs": ["D04"]},
    {"id": "L-D04-5", "q": "Nghỉ không lương có làm thay đổi ngày đánh giá thử việc theo lịch không?", "must_include": ["không làm thay đổi ngày đánh giá theo lịch"], "docs": ["D04"]},
]


BLOCKS = {
    "D01": D01,
    "D02": D02,
    "D03a": D03a,
    "D03b": D03b,
    "D03c": D03c,
    "D04": D04,
}
STYLE = {}
QA = QA_D01 + QA_D02 + QA_D03 + QA_D04
