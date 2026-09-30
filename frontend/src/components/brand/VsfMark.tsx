import { useId } from "react";

/**
 * Dấu hiệu nhận diện VSF Onboarding: ô vuông bo góc chia chéo hai màu (xanh dương và đỏ) với chữ "V" trắng ở giữa.
 * Dùng chung cho trang chủ, trang đăng nhập, khung HR/Admin và khung nhân viên để mọi nơi giống hệt nhau.
 */
export function VsfMark({ size = 32, className }: { size?: number; className?: string }) {
  // Nhiều logo trên cùng một trang không được dùng chung id vùng cắt.
  const clipId = useId().replace(/:/g, "");

  return (
    <svg aria-hidden="true" className={className} height={size} viewBox="0 0 32 32" width={size}>
      <defs>
        <clipPath id={clipId}>
          <rect height="32" rx="7" width="32" />
        </clipPath>
      </defs>
      <g clipPath={`url(#${clipId})`}>
        <rect fill="#1a6fc0" height="32" width="32" />
        <path d="M32 6 32 32 6 32Z" fill="#d9343f" />
      </g>
      <path d="M9 10 16 23l7-13" fill="none" stroke="#fff" strokeLinecap="round" strokeLinejoin="round" strokeWidth="3.6" />
    </svg>
  );
}
