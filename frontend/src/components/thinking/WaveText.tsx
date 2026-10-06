import styles from "./WaveText.module.scss";

/**
 * Chữ lượn sóng cho trạng thái "đang xử lý" (thay vòng xoay): mỗi ký tự nhấp nhô lệch pha nhau một chút. Đọc màn hình đọc cả
 * câu một lần (`aria-label`), các ký tự riêng lẻ ẩn đi. Tắt chuyển động khi người dùng chọn giảm hiệu ứng.
 */
export function WaveText({ text }: { text: string }) {
  return (
    <span aria-label={text} className={styles.wave} role="status">
      {Array.from(text).map((char, index) => (
        <span aria-hidden="true" className={styles.char} key={index} style={{ animationDelay: `${index * 70}ms` }}>
          {char === " " ? "\u00a0" : char}
        </span>
      ))}
    </span>
  );
}
