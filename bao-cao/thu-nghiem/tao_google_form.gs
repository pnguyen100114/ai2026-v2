/**
 * Tạo Google Form khảo sát sau buổi dùng thử Mimo (Việc 2 trong bao-cao/KE_HOACH_THU_NGHIEM.md).
 *
 * Cách chạy (5 phút):
 *   1. Mở https://script.google.com → Dự án mới → xoá hết code mẫu → dán toàn bộ file này.
 *   2. Bấm Chạy (hàm taoForm). Lần đầu Google hỏi quyền tạo Form trên Drive của em → Cho phép.
 *   3. Xem nhật ký thực thi: có link để gửi học sinh và link để sửa Form.
 *   4. Sau buổi thử: trong Form → Câu trả lời → Liên kết với Trang tính → Tệp → Tải xuống CSV,
 *      rồi chạy: python bao-cao/thu-nghiem/tong_hop.py khao-sat <file.csv>
 *
 * Tiêu đề câu hỏi phải giữ nguyên: tong_hop.py tìm cột theo các tiêu đề này.
 */
function taoForm() {
  var form = FormApp.create('Mimo - khảo sát sau buổi dùng thử');
  form.setDescription(
    'Phiếu không ghi tên, chỉ để nhóm biết Mimo giúp em được tới đâu. Em trả lời thật lòng nhé, ' +
    'chê cũng được, chê càng cụ thể càng có ích. Khoảng 5 phút.');
  form.setCollectEmail(false);
  form.setLimitOneResponsePerUser(false);
  form.setShowLinkToRespondAgain(false);

  form.addListItem().setTitle('Em học lớp mấy?')
    .setChoiceValues(['Lớp 6', 'Lớp 7', 'Lớp 8', 'Lớp 9']).setRequired(true);
  form.addTextItem().setTitle('Hôm nay em đã làm bài nào với Mimo?')
    .setHelpText('Ví dụ: Toán 8, bài tập 2.3 trang 32');

  form.addMultipleChoiceItem().setTitle('Có lúc nào Mimo giải hết bài cho em không?')
    .setChoiceValues(['Không bao giờ', '1 lần', 'Nhiều lần']).setRequired(true);

  form.addScaleItem().setTitle('Sau gợi ý của Mimo, em có tự làm tiếp được bước sau không?')
    .setBounds(1, 5).setLabels('Không làm được', 'Tự làm hết').setRequired(true);

  form.addMultipleChoiceItem().setTitle('Em có thử năn nỉ Mimo cho đáp án không?')
    .setChoiceValues(['Có', 'Không']).setRequired(true);
  form.addParagraphTextItem().setTitle('Nếu có năn nỉ, Mimo phản ứng thế nào?');

  form.addMultipleChoiceItem().setTitle('Em có bấm xem trang sách Mimo trích không?')
    .setChoiceValues(['Không bấm', 'Bấm, thấy khớp với lời Mimo giảng', 'Bấm, thấy chỗ không khớp'])
    .setRequired(true);

  form.addParagraphTextItem().setTitle('Em có phát hiện chỗ nào Mimo giảng sai không? Chỗ nào?')
    .setHelpText('Không thấy thì bỏ trống.');

  form.addScaleItem().setTitle('So với hỏi ChatGPT/Gemini, Mimo giúp em hiểu bài hơn hay kém hơn?')
    .setBounds(1, 5).setLabels('Kém hơn nhiều', 'Hơn nhiều')
    .setHelpText('Chưa dùng ChatGPT/Gemini bao giờ thì bỏ trống.');

  form.addScaleItem().setTitle('Lần sau làm bài tập về nhà, em có muốn dùng Mimo không?')
    .setBounds(1, 5).setLabels('Không muốn', 'Rất muốn').setRequired(true);
  form.addParagraphTextItem().setTitle('Vì sao em muốn hoặc không muốn dùng tiếp?');

  form.addParagraphTextItem().setTitle('Điều em khó chịu nhất khi dùng Mimo là gì?');

  Logger.log('Link gửi học sinh: ' + form.getPublishedUrl());
  Logger.log('Link sửa Form:     ' + form.getEditUrl());
}
