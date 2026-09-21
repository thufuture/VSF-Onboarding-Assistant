/** Vai trò hệ thống (khớp `UserRoleDTO` ở `backend/src/dto/response/auth_response_dto.py`). */
export type UserRoleDTO = "USER" | "HR" | "ADMIN";

/** Phản hồi của `POST /auth/login`, `GET /auth/me`, `POST /auth/refresh` (khớp `SessionUserResponseDTO`). */
export type SessionUserResponseDTO = {
  id: number;
  email: string;
  display_name: string;
  role: UserRoleDTO;
  /** Tên phòng ban (đội) của người dùng; nhiều đội nối bằng ", "; chưa thuộc đội nào thì null. */
  department: string | null;
  /** Thời điểm hết hạn của phiên, ISO 8601. */
  expires_at: string;
};
