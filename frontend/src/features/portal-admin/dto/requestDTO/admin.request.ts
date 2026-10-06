export type CreateUserRequestDTO = {
  display_name: string;
  email: string;
  role: "USER" | "HR" | "ADMIN";
  team_id: number | null;
};

export type UpdateUserRequestDTO = {
  display_name: string;
  email: string;
  role: "USER" | "HR" | "ADMIN";
};

export type CreateTeamRequestDTO = {
  name: string;
  code: string;
  hr_user_id: number | null;
  copy_shared_template: boolean;
};

export type UpdateTeamRequestDTO = {
  name: string;
  hr_user_id: number | null;
};

export type CreateMembershipRequestDTO = {
  team_id: number;
  user_id: number;
};
