import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import styles from "./MarkdownText.module.scss";

/**
 * Văn bản có định dạng Markdown gọn cho khung trò chuyện và thẻ hướng dẫn: in đậm, danh sách, liên kết, mã. Không cho chèn HTML
 * (react-markdown bỏ qua HTML thô), liên kết mở tab mới.
 */
export function MarkdownText({ children, className }: { children: string; className?: string }) {
  return (
    <div className={`${styles.md} ${className ?? ""}`}>
      <ReactMarkdown
        components={{
          a: ({ children, href }) => (
            <a href={href} rel="noopener noreferrer" target="_blank">
              {children}
            </a>
          ),
        }}
        remarkPlugins={[remarkGfm]}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
