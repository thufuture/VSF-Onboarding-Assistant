/** Yêu cầu của `POST /api/v1/auth/login` (khớp `backend/src/dto/request/auth_request_dto.py`). */
export type LoginRequestDTO = {
  email: string;
  password: string;
};
