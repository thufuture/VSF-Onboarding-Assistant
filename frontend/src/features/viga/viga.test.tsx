import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import viMessages from "../../../messages/vi.json";
import { SessionProvider } from "@/features/auth/SessionProvider";
import type { SessionUserResponseDTO } from "@/features/auth/dto/responseDTO/auth.response";
import { VigaPanel } from "@/features/portal-employee/VigaPanel";
import { useVigaPanel } from "@/features/portal-employee/vigaPanelStore";

import { VigaError, vigaApi } from "./api";
import type {
  ContentGapResponseDTO,
  ConversationMessageResponseDTO,
  DissatisfiedGroupResponseDTO,
  TicketDetailResponseDTO,
  TicketSummaryResponseDTO,
  VigaAnswerResponseDTO,
} from "./dto/responseDTO/viga.response";
import { HrTicketsPage } from "./HrTicketsPage";
import { TicketThread } from "./TicketThread";
import { VigaReply } from "./VigaReply";
import { VigaFeedbackPage } from "./VigaFeedbackPage";
import { VigaPage } from "./VigaPage";

const push = vi.fn();
const jobHooks = vi.hoisted(() => ({ done: null as null | ((job: { status: string }) => void) }));
const searchState = vi.hoisted(() => ({ value: "" }));

vi.mock("@/i18n/navigation", () => ({
  Link: ({ href, children, ...rest }: { href: string; children: ReactNode; className?: string }) => (
    <a href={`/vi${href}`} {...rest}>
      {children}
    </a>
  ),
  usePathname: () => "/me",
  useRouter: () => ({ push, replace: vi.fn() }),
}));
vi.mock("next/navigation", () => ({ useSearchParams: () => new URLSearchParams(searchState.value) }));
vi.mock("@/features/portal-hr/useJob", () => ({
  useJob: (id: number | null, onDone: (job: { status: string }) => void) => {
    jobHooks.done = onDone;
    return { job: id ? { progress_percent: 40, stage: "Đang tạo embedding", status: "RUNNING" } : null, lost: false };
  },
}));
vi.mock("@/features/chat/DocumentModal", () => ({
  DocumentModal: ({
    documentTitle,
    sectionHeading,
    quote,
  }: {
    documentTitle: string;
    sectionHeading: string | null;
    quote?: string | null;
  }) => (
    <div data-quote={quote ?? ""} role="dialog">
      {`Tài liệu mở: ${documentTitle} / ${sectionHeading}`}
    </div>
  ),
}));
vi.mock("@/features/viga/api", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/features/viga/api")>();
  return {
    ...original,
    vigaApi: {
      ask: vi.fn(),
      listConversations: vi.fn(),
      getConversation: vi.fn(),
      renameConversation: vi.fn(),
      deleteConversation: vi.fn(),
      createTicket: vi.fn(),
      listMyTickets: vi.fn(),
      listStaffTickets: vi.fn(),
      getTicket: vi.fn(),
      addTicketMessage: vi.fn(),
      claimTicket: vi.fn(),
      setTicketStatus: vi.fn(),
      listContentGaps: vi.fn(),
      resolveContentGap: vi.fn(),
      recheckContentGap: vi.fn(),
      supplementContentGap: vi.fn(),
      recheckDissatisfied: vi.fn(),
      supplementDissatisfied: vi.fn(),
      listDissatisfied: vi.fn(),
      resolveDissatisfied: vi.fn(),
      feedbackSummary: vi.fn(),
      rateAnswer: vi.fn(),
      clearRating: vi.fn(),
      markTaskOpened: vi.fn(),
      getUnreadTickets: vi.fn(),
      markTicketRead: vi.fn(),
    },
  };
});

const api = vi.mocked(vigaApi);
const viga = viMessages.employee.viga;
const hrText = viMessages.viga;

const USER: SessionUserResponseDTO = {
  id: 7,
  email: "user@vsf-demo.example",
  display_name: "Nguyễn Văn An",
  role: "USER",
  department: "Khối Dữ liệu",
  expires_at: "2026-09-30T10:00:00Z",
};

function reply(overrides: Partial<VigaAnswerResponseDTO>): VigaAnswerResponseDTO {
  return {
    conversation_id: 3,
    message_id: 9,
    new_conversation: true,
    response_type: "INFO",
    message: "",
    message_key: null,
    message_params: {},
    claims: [],
    blocking_tasks: [],
    suggested_actions: [],
    sources: [],
    can_report_to_hr: false,
    assumed_task_title: null,
    route: "LLM",
    ...overrides,
  };
}

function Opener() {
  const { toggle } = useVigaPanel();
  return (
    <button onClick={toggle} type="button">
      mở viga
    </button>
  );
}

function renderPanel() {
  render(
    <NextIntlClientProvider locale="vi" messages={viMessages}>
      <SessionProvider initialUser={USER}>
        <Opener />
        <VigaPanel />
      </SessionProvider>
    </NextIntlClientProvider>,
  );
  // Trạng thái ngăn Viga nằm ngoài cây React (kho dùng chung), nên có thể còn mở từ test trước: chỉ bấm mở khi đang đóng.
  if (!screen.queryByRole("complementary", { name: viga.title })) {
    fireEvent.click(screen.getByRole("button", { name: "mở viga" }));
  }
  return screen.getByRole("complementary", { name: viga.title });
}

async function ask(panel: HTMLElement, text: string) {
  fireEvent.change(within(panel).getByLabelText(viga.inputLabel), { target: { value: text } });
  fireEvent.click(within(panel).getByRole("button", { name: viga.send }));
}

beforeEach(() => {
  vi.resetAllMocks();
});

describe("Ngăn Viga (API thật)", () => {
  it("câu trả lời tài liệu hiện kèm trích dẫn nguyên văn và mở được tài liệu nguồn", async () => {
    api.ask.mockResolvedValue(
      reply({
        response_type: "ANSWER",
        claims: [
          {
            question: "Nghỉ phép năm?",
            response_type: "ANSWER",
            text: "Nhân viên chính thức được nghỉ 12 ngày phép năm.",
            quote: "được nghỉ phép năm 12 ngày mỗi năm",
            source: {
              document_title: "Quy định nghỉ phép",
              version_label: "1.0",
              section_heading: "Nghỉ phép năm",
              document_url: "documents/a.docx",
              version_id: 5,
            },
          },
        ],
      }),
    );
    const panel = renderPanel();

    await ask(panel, "Nghỉ phép năm được bao nhiêu ngày?");

    expect(await within(panel).findByText("Nhân viên chính thức được nghỉ 12 ngày phép năm.")).toBeInTheDocument();
    expect(within(panel).getByText("được nghỉ phép năm 12 ngày mỗi năm")).toBeInTheDocument();
    expect(within(panel).getByText(viga.type.ANSWER)).toBeInTheDocument();
    fireEvent.click(within(panel).getByRole("button", { name: /Quy định nghỉ phép · 1\.0 · Nghỉ phép năm/ }));
    expect(await screen.findByRole("dialog")).toHaveTextContent("Tài liệu mở: Quy định nghỉ phép / Nghỉ phép năm");
  });

  it("nối tiếp trong cùng cuộc trò chuyện gửi lại conversation_id; cuộc mới thì bỏ", async () => {
    api.ask.mockResolvedValue(reply({ conversation_id: 42, response_type: "INFO", message_key: "smalltalk" }));
    const panel = renderPanel();

    await ask(panel, "xin chào");
    await within(panel).findByText(viga.reply.smalltalk);
    await ask(panel, "cảm ơn");
    await waitFor(() => expect(api.ask).toHaveBeenCalledTimes(2));
    expect(api.ask).toHaveBeenNthCalledWith(1, { question: "xin chào", conversation_id: null });
    expect(api.ask).toHaveBeenNthCalledWith(2, { question: "cảm ơn", conversation_id: 42 });

    fireEvent.click(within(panel).getByRole("button", { name: viga.history.new }));
    await ask(panel, "câu mới");
    await waitFor(() => expect(api.ask).toHaveBeenCalledTimes(3));
    expect(api.ask).toHaveBeenNthCalledWith(3, { question: "câu mới", conversation_id: null });
  });

  it("chưa có căn cứ thì nói thẳng và gợi ý gửi HR; gửi sau khi nhân viên xem và sửa", async () => {
    api.ask.mockResolvedValue(
      reply({ response_type: "NO_BASIS", message_key: "noBasis", can_report_to_hr: true, conversation_id: 8 }),
    );
    api.createTicket.mockResolvedValue({ id: 123 } as TicketSummaryResponseDTO);
    const panel = renderPanel();

    await ask(panel, "Quy định gửi xe máy là gì?");
    expect(await within(panel).findByText(viga.reply.noBasis)).toBeInTheDocument();
    fireEvent.click(within(panel).getByRole("button", { name: viga.report.button }));

    // Hộp xác nhận hiện sẵn câu hỏi gốc để nhân viên sửa; chưa gửi gì tới khi bấm Gửi.
    const dialog = await screen.findByRole("dialog");
    const question = within(dialog).getByLabelText(viga.report.question);
    expect(question).toHaveValue("Quy định gửi xe máy là gì?");
    expect(api.createTicket).not.toHaveBeenCalled();
    fireEvent.change(question, { target: { value: "Quy định gửi xe máy ở tầng hầm là gì?" } });
    fireEvent.change(within(dialog).getByLabelText(viga.report.note), { target: { value: "Cần gấp" } });
    fireEvent.click(within(dialog).getByRole("button", { name: viga.report.send }));

    await waitFor(() =>
      expect(api.createTicket).toHaveBeenCalledWith({
        question: "Quy định gửi xe máy ở tầng hầm là gì?",
        note: "Cần gấp",
        employee_task_id: null,
        conversation_id: 8,
        attachment_ids: [],
      }),
    );
    expect(await within(panel).findByText(`Đã gửi cho HR (mã #123). Bạn theo dõi phản hồi ở mục Yêu cầu.`)).toBeInTheDocument();
    expect(within(panel).queryByRole("button", { name: viga.report.button })).not.toBeInTheDocument();
  });

  it("không gợi ý gửi HR cho câu đã trả lời hoặc cần làm rõ", async () => {
    api.ask.mockResolvedValue(reply({ response_type: "CLARIFY", message: "Bạn đang nói về việc nào?", can_report_to_hr: false }));
    const panel = renderPanel();

    await ask(panel, "cái này sao ấy");

    expect(await within(panel).findByText("Bạn đang nói về việc nào?")).toBeInTheDocument();
    expect(within(panel).queryByRole("button", { name: viga.report.button })).not.toBeInTheDocument();
  });

  it("báo rõ khi ticket vượt giới hạn hoặc trùng", async () => {
    api.ask.mockResolvedValue(reply({ response_type: "OUT_OF_SCOPE", message_key: "outOfScope", can_report_to_hr: true }));
    api.createTicket.mockRejectedValue(new VigaError("unavailable", "TICKET_DAILY_LIMIT"));
    const panel = renderPanel();

    await ask(panel, "Mentor của mình là ai?");
    fireEvent.click(await within(panel).findByRole("button", { name: viga.report.button }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: viga.report.send }));

    expect(await within(dialog).findByRole("alert")).toHaveTextContent(viga.report.errors.TICKET_DAILY_LIMIT);
  });

  it("đang hỏi quá nhanh thì báo số giây chờ; lỗi mạng và lỗi máy chủ có thông báo riêng", async () => {
    api.ask.mockRejectedValueOnce(new VigaError("throttled", "TOO_MANY_QUESTIONS", 12));
    api.ask.mockRejectedValueOnce(new VigaError("network"));
    const panel = renderPanel();

    await ask(panel, "câu một");
    expect(await within(panel).findByText("Bạn hỏi nhanh quá, thử lại sau 12 giây nhé.")).toBeInTheDocument();
    await ask(panel, "câu hai");
    expect(await within(panel).findByText(viga.errors.network)).toBeInTheDocument();
  });

  it("việc có giả định thì nói rõ Viga đang hiểu việc nào", async () => {
    api.ask.mockResolvedValue(
      reply({
        response_type: "INFO",
        message_key: "taskReady",
        message_params: { title: "Nhận laptop" },
        assumed_task_title: "Nhận laptop",
      }),
    );
    const panel = renderPanel();

    await ask(panel, "task này sao chưa làm được");

    expect(await within(panel).findByText("Mình đang hiểu bạn nói về việc “Nhận laptop”.")).toBeInTheDocument();
  });

  it("lịch sử: liệt kê, mở lại đúng như lúc đã hỏi, đổi tên và xóa", async () => {
    const stored: ConversationMessageResponseDTO[] = [
      { id: 1, role: "USER", content: "Hôm nay làm gì?", response_type: null, payload: {}, created_at: "2026-10-01T01:00:00Z" },
      {
        id: 2,
        role: "ASSISTANT",
        content: "Ngày 1: ...",
        response_type: "DAY_PLAN",
        payload: {
          message_key: "dayPlan",
          message_params: { day: "Ngày 1", ready: 2, total: 5 },
          actions: [{ type: "OPEN_TASK", title: "Nhận laptop", task_id: 11, stage_id: null }],
          claims: [],
          blocking_tasks: [],
          sources: [],
          can_report: false,
        },
        created_at: "2026-10-01T01:00:01Z",
      },
    ];
    api.listConversations.mockResolvedValue([
      { id: 3, title: "Hôm nay làm gì?", created_at: "2026-10-01T01:00:00Z", updated_at: "2026-10-01T01:00:01Z" },
    ]);
    api.getConversation.mockResolvedValue({
      conversation: { id: 3, title: "Hôm nay làm gì?", created_at: "2026-10-01T01:00:00Z", updated_at: "2026-10-01T01:00:01Z" },
      messages: stored,
    });
    api.renameConversation.mockResolvedValue({
      id: 3,
      title: "Việc ngày đầu",
      created_at: "2026-10-01T01:00:00Z",
      updated_at: "2026-10-01T01:00:01Z",
    });
    api.deleteConversation.mockResolvedValue();
    const panel = renderPanel();

    fireEvent.click(within(panel).getByRole("button", { name: viga.history.title }));
    const list = await within(panel).findByRole("region", { name: viga.history.title });

    fireEvent.click(within(list).getByRole("button", { name: /Hôm nay làm gì\?/ }));
    expect(await within(panel).findByText("Ngày 1: bạn làm được ngay 2 việc trên tổng 5 việc của ngày.")).toBeInTheDocument();
    expect(within(panel).getByRole("button", { name: "Mở: Nhận laptop" })).toBeInTheDocument();

    // Đổi tên rồi xóa.
    fireEvent.click(within(panel).getByRole("button", { name: viga.history.title }));
    const reopened = await within(panel).findByRole("region", { name: viga.history.title });
    fireEvent.click(within(reopened).getByRole("button", { name: viga.history.rename }));
    const input = within(reopened).getByRole("textbox", { name: viga.history.rename });
    fireEvent.change(input, { target: { value: "Việc ngày đầu" } });
    fireEvent.submit(input);
    await waitFor(() => expect(api.renameConversation).toHaveBeenCalledWith(3, "Việc ngày đầu"));
    fireEvent.click(await within(reopened).findByRole("button", { name: viga.history.delete }));
    await waitFor(() => expect(api.deleteConversation).toHaveBeenCalledWith(3));
    expect(await within(reopened).findByText(viga.history.empty)).toBeInTheDocument();
  });
});

function ticket(overrides: Partial<TicketSummaryResponseDTO>): TicketSummaryResponseDTO {
  return {
    id: 1,
    subject: "Mình chưa nhận được laptop",
    status: "OPEN",
    source: "VIGA",
    created_at: "2026-10-01T01:00:00Z",
    updated_at: "2026-10-01T01:00:00Z",
    requester_name: "Trần Anh Thư",
    requester_email: "thu.tran@vsf-demo.example",
    team_name: "Phòng nhân sự",
    assigned_hr_name: null,
    related_task_title: null,
    message_count: 1,
    last_sender_is_staff: false,
    resolution_note: null,
    ...overrides,
  };
}

function detail(summary: TicketSummaryResponseDTO): TicketDetailResponseDTO {
  return {
    ticket: summary,
    messages: [
      { id: 1, sender_name: "Trần Anh Thư", sender_role: "USER", body: "Mình chưa nhận được laptop", created_at: "2026-10-01T01:00:00Z", mine: false },
    ],
  };
}

/** Ô chọn tự vẽ (PortalSelect): mở danh sách rồi bấm một dòng, như người dùng thật. */
function pick(label: string, option: string | RegExp) {
  fireEvent.click(screen.getByRole("combobox", { name: label }));
  fireEvent.click(within(screen.getByRole("listbox", { name: label })).getByRole("option", { name: option }));
}

function renderHr(ui: ReactNode) {
  return render(<NextIntlClientProvider locale="vi" messages={viMessages}>{ui}</NextIntlClientProvider>);
}

describe("Câu hỏi nhiều ý", () => {
  it("mỗi ý một thẻ có số thứ tự và câu hỏi con; ý chưa có căn cứ cũng có thẻ riêng", () => {
    const source = { document_title: "Hướng dẫn ngày 1", version_label: "1.0", section_heading: "Hồ sơ", document_url: "/d/1", version_id: 1 };
    const reply = {
      conversation_id: 1,
      message_id: 0,
      new_conversation: false,
      response_type: "ANSWER",
      message: "",
      message_key: null,
      message_params: {},
      claims: [
        { question: "Chưa có VNeID thì sao?", response_type: "ANSWER", text: "Photo công chứng.", quote: "phải photo công chứng", source },
        { question: "Dùng CMND được không?", response_type: "NO_BASIS", text: null, quote: null, source: null },
        { question: "Không đăng nhập được Teams?", response_type: "ANSWER", text: "Đăng nhập lại cả hai ứng dụng.", quote: "Đăng xuất, đăng nhập lại", source },
      ],
      blocking_tasks: [],
      suggested_actions: [],
      sources: [],
      can_report_to_hr: false,
      unanswered: [],
      assumed_task_title: null,
      route: "LLM",
    } as VigaAnswerResponseDTO;
    render(
      <NextIntlClientProvider locale="vi" messages={viMessages}>
        <VigaReply onReport={() => undefined} reply={reply} sentTicketId={null} />
      </NextIntlClientProvider>,
    );

    for (const n of [1, 2, 3]) expect(screen.getByText(`Ý ${n}`)).toBeInTheDocument();
    expect(screen.getByText("Chưa có VNeID thì sao?")).toBeInTheDocument();
    expect(screen.getByText("Dùng CMND được không?")).toBeInTheDocument();
    expect(screen.getByText(viMessages.employee.viga.claim.partNoBasis)).toBeInTheDocument();
    expect(screen.getByText("Photo công chứng.")).toBeInTheDocument();
    expect(screen.getByText("Đăng nhập lại cả hai ứng dụng.")).toBeInTheDocument();
  });

  it("câu một ý không có thẻ đánh số", () => {
    const reply = {
      conversation_id: 1,
      message_id: 0,
      new_conversation: false,
      response_type: "ANSWER",
      message: "",
      message_key: null,
      message_params: {},
      claims: [{ question: "Laptop nhận ở đâu?", response_type: "ANSWER", text: "Tầng 12.", quote: null, source: null }],
      blocking_tasks: [],
      suggested_actions: [],
      sources: [],
      can_report_to_hr: false,
      unanswered: [],
      assumed_task_title: null,
      route: "LLM",
    } as VigaAnswerResponseDTO;
    render(
      <NextIntlClientProvider locale="vi" messages={viMessages}>
        <VigaReply onReport={() => undefined} reply={reply} sentTicketId={null} />
      </NextIntlClientProvider>,
    );

    expect(screen.getByText("Tầng 12.")).toBeInTheDocument();
    expect(screen.queryByText("Ý 1")).not.toBeInTheDocument();
  });
});

describe("Khung trao đổi tự cập nhật", () => {
  it("tin mới của bên kia hiện ra không cần tải lại trang, rồi đánh dấu đã xem", async () => {
    const open = ticket({ id: 1, assigned_hr_name: "HR Hồng", status: "IN_PROGRESS" });
    const onChanged = vi.fn();
    api.getTicket.mockResolvedValueOnce(detail(open));
    api.markTicketRead.mockResolvedValue({ count: 0, ticket_ids: [] });
    render(
      <NextIntlClientProvider locale="vi" messages={viMessages}>
        <TicketThread onChanged={onChanged} staff={false} ticketId={1} />
      </NextIntlClientProvider>,
    );
    expect((await screen.findAllByText("Mình chưa nhận được laptop")).length).toBeGreaterThan(0);

    api.getTicket.mockResolvedValue({
      ...detail(open),
      messages: [
        ...detail(open).messages,
        { id: 2, sender_name: "HR Hồng", sender_role: "HR", body: "Chiều nay giao máy.", created_at: "2026-10-01T02:00:00Z", mine: false },
      ],
    });

    expect(await screen.findByText("Chiều nay giao máy.", {}, { timeout: 7000 })).toBeInTheDocument();
    expect(onChanged).toHaveBeenCalled();
    expect(api.markTicketRead).toHaveBeenLastCalledWith(1);
  }, 12000);
});

describe("Ticket sự cố của HR", () => {
  it("hiện hàng đợi, lọc theo trạng thái, nhận xử lý và trả lời", async () => {
    const open = ticket({ id: 1 });
    const resolved = ticket({ id: 2, subject: "Câu đã xong", status: "RESOLVED" });
    api.listStaffTickets.mockResolvedValue([open, resolved]);
    api.getTicket.mockResolvedValue(detail(open));
    api.claimTicket.mockResolvedValue(detail({ ...open, status: "IN_PROGRESS", assigned_hr_name: "HR Hồng" }));
    api.addTicketMessage.mockResolvedValue({
      ...detail({ ...open, status: "IN_PROGRESS", assigned_hr_name: "HR Hồng" }),
      messages: [
        ...detail(open).messages,
        { id: 2, sender_name: "HR Hồng", sender_role: "HR", body: "Chiều nay giao máy.", created_at: "2026-10-01T02:00:00Z", mine: true },
      ],
    });
    renderHr(<HrTicketsPage />);

    expect(await screen.findByText("Mình chưa nhận được laptop")).toBeInTheDocument();
    expect(screen.getByText(hrText.ticket.unclaimed)).toBeInTheDocument(); // chưa có HR nhận
    pick(hrText.ticket.filterLabel, new RegExp(hrText.ticket.status.RESOLVED));
    expect(screen.queryByText("Mình chưa nhận được laptop")).not.toBeInTheDocument();
    expect(screen.getByText("Câu đã xong")).toBeInTheDocument();
    pick(hrText.ticket.filterLabel, new RegExp(`^${hrText.ticket.filterAll}`));

    fireEvent.click(screen.getByRole("button", { name: /Mình chưa nhận được laptop/ }));
    fireEvent.click(await screen.findByRole("button", { name: hrText.ticket.claim }));
    await waitFor(() => expect(api.claimTicket).toHaveBeenCalledWith(1));
    expect(await screen.findByText("HR phụ trách: HR Hồng")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(hrText.ticket.replyLabel), { target: { value: "Chiều nay giao máy." } });
    fireEvent.click(screen.getByRole("button", { name: hrText.ticket.send }));
    await waitFor(() => expect(api.addTicketMessage).toHaveBeenCalledWith(1, { body: "Chiều nay giao máy.", attachment_ids: [] }));
    expect(await screen.findByText("Chiều nay giao máy.")).toBeInTheDocument();
  });

  it("ticket có tin chưa xem hiện chấm; mở ticket thì đánh dấu đã xem rồi tải lại danh sách", async () => {
    const fresh = ticket({ id: 1, unread: true });
    const old = ticket({ id: 2, subject: "Câu đã xem", unread: false });
    api.listStaffTickets.mockResolvedValueOnce([fresh, old]).mockResolvedValue([{ ...fresh, unread: false }, old]);
    api.getTicket.mockResolvedValue(detail(fresh));
    api.markTicketRead.mockResolvedValue({ count: 0, ticket_ids: [] });
    renderHr(<HrTicketsPage />);

    const row = await screen.findByRole("button", { name: /Mình chưa nhận được laptop/ });
    expect(within(row).getByRole("status", { name: hrText.ticket.unread })).toBeInTheDocument();
    expect(within(screen.getByRole("button", { name: /Câu đã xem/ })).queryByRole("status")).not.toBeInTheDocument();

    fireEvent.click(row);

    await waitFor(() => expect(api.markTicketRead).toHaveBeenCalledWith(1));
    await waitFor(() => expect(within(screen.getByRole("button", { name: /Mình chưa nhận được laptop/ })).queryByRole("status")).not.toBeInTheDocument());
  });

  it("tìm theo tên, email hoặc tiêu đề (không phân biệt dấu) và báo khi không có kết quả", async () => {
    const thu = ticket({ id: 1 });
    const hong = ticket({
      id: 2,
      subject: "Quên mật khẩu email",
      requester_name: "Phạm Thị Hồng",
      requester_email: "hong.pham@vsf-demo.example",
    });
    api.listStaffTickets.mockResolvedValue([thu, hong]);
    renderHr(<HrTicketsPage />);
    await screen.findByText("Mình chưa nhận được laptop");
    const search = screen.getByLabelText(hrText.ticket.searchLabel);

    fireEvent.change(search, { target: { value: "pham" } }); // tên "Phạm", không gõ dấu
    expect(screen.getByText("Quên mật khẩu email")).toBeInTheDocument();
    expect(screen.queryByText("Mình chưa nhận được laptop")).not.toBeInTheDocument();
    expect(screen.getByText("Hiển thị 1 trên 2 ticket")).toBeInTheDocument();

    fireEvent.change(search, { target: { value: "thu.tran@" } }); // theo email
    expect(screen.getByText("Mình chưa nhận được laptop")).toBeInTheDocument();
    expect(screen.queryByText("Quên mật khẩu email")).not.toBeInTheDocument();

    fireEvent.change(search, { target: { value: "không-có-ai-như-vậy" } });
    expect(screen.getByText(hrText.ticket.noMatch)).toBeInTheDocument();
  });

  it("đổi trạng thái kèm ghi chú kết quả và nhắc đóng ticket không đổi task", async () => {
    const claimed = ticket({ id: 1, status: "IN_PROGRESS", assigned_hr_name: "HR Hồng" });
    api.listStaffTickets.mockResolvedValue([claimed]);
    api.getTicket.mockResolvedValue(detail(claimed));
    api.setTicketStatus.mockResolvedValue(detail({ ...claimed, status: "RESOLVED", resolution_note: "Đã giao laptop." }));
    renderHr(<HrTicketsPage />);

    fireEvent.click(await screen.findByRole("button", { name: /Mình chưa nhận được laptop/ }));
    expect(await screen.findByText(hrText.ticket.taskUnchanged)).toBeInTheDocument();
    await new Promise((resolve) => setTimeout(resolve, 60));
    expect(api.getTicket).toHaveBeenCalledTimes(1); // mở một ticket chỉ tải một lần, không lặp khi vẽ lại
    pick(hrText.ticket.statusLabel, hrText.ticket.status.RESOLVED);
    fireEvent.change(screen.getByLabelText(hrText.ticket.noteLabel), { target: { value: "Đã giao laptop." } });
    fireEvent.click(screen.getByRole("button", { name: hrText.ticket.saveStatus }));

    await waitFor(() =>
      expect(api.setTicketStatus).toHaveBeenCalledWith(1, { status: "RESOLVED", resolution_note: "Đã giao laptop." }),
    );
    expect(await screen.findByText("Kết quả: Đã giao laptop.")).toBeInTheDocument();
  });

  it("ticket đã đóng không cho trả lời thêm", async () => {
    const closed = ticket({ id: 1, status: "CLOSED", assigned_hr_name: "HR Hồng" });
    api.listStaffTickets.mockResolvedValue([closed]);
    api.getTicket.mockResolvedValue(detail(closed));
    renderHr(<HrTicketsPage />);

    fireEvent.click(await screen.findByRole("button", { name: /Mình chưa nhận được laptop/ }));

    expect(await screen.findByText(hrText.ticket.closedNote)).toBeInTheDocument();
    expect(screen.queryByLabelText(hrText.ticket.replyLabel)).not.toBeInTheDocument();
  });
});

describe("Đánh giá 👍/👎 và định dạng câu trả lời", () => {
  const answered = (extra: Partial<VigaAnswerResponseDTO> = {}) =>
    reply({
      response_type: "ANSWER",
      claims: [
        {
          question: "Hồ sơ?",
          response_type: "ANSWER",
          text: "Bạn nộp **CV** và các giấy tờ sau:\n\n* Lý lịch tư pháp\n* Căn cước công dân",
          quote: "• CV. • Lý lịch tư pháp",
          source: {
            document_title: "Hướng dẫn ngày 1",
            version_label: "1.0",
            section_heading: "2. Hồ sơ",
            document_url: "x",
            version_id: 5,
          },
        },
      ],
      ...extra,
    });

  it("dựng Markdown: in đậm và danh sách, không còn dấu ** hay * trơ trọi", async () => {
    api.ask.mockResolvedValue(answered());
    const panel = renderPanel();
    await ask(panel, "Hồ sơ cần nộp gồm gì?");

    expect(await within(panel).findByText("CV")).toContainHTML("<strong>CV</strong>");
    expect(within(panel).getAllByRole("listitem").map((item) => item.textContent)).toEqual(
      expect.arrayContaining(["Lý lịch tư pháp", "Căn cước công dân"]),
    );
    expect(panel.textContent).not.toContain("**");
  });

  it("nút nguồn mở tài liệu kèm đoạn trích để tô đúng đoạn", async () => {
    api.ask.mockResolvedValue(answered());
    const panel = renderPanel();
    await ask(panel, "Hồ sơ cần nộp gồm gì?");

    fireEvent.click(await within(panel).findByRole("button", { name: /Hướng dẫn ngày 1/ }));
    const dialog = await screen.findByRole("dialog");
    expect(dialog).toHaveAttribute("data-quote", "• CV. • Lý lịch tư pháp");
  });

  it("trả lời một phần thì liệt kê ý tài liệu chưa quy định", async () => {
    api.ask.mockResolvedValue(answered({ unanswered: ["Có được đổi máy khác không?"], can_report_to_hr: true }));
    const panel = renderPanel();
    await ask(panel, "Nhận laptop ở đâu và có đổi máy được không?");

    expect(await within(panel).findByText(viga.claim.unansweredTitle)).toBeInTheDocument();
    expect(within(panel).getByText("Có được đổi máy khác không?")).toBeInTheDocument();
    expect(within(panel).getByRole("button", { name: viga.report.button })).toBeInTheDocument();
  });

  it("👍 gửi đánh giá, bấm lại thì gỡ", async () => {
    api.ask.mockResolvedValue(answered());
    api.rateAnswer.mockResolvedValue({ rating: "UP", reason: null, comment: null });
    api.clearRating.mockResolvedValue();
    const panel = renderPanel();
    await ask(panel, "Hồ sơ cần nộp gồm gì?");

    const up = await within(panel).findByRole("button", { name: viga.feedback.up });
    fireEvent.click(up);
    await waitFor(() => expect(api.rateAnswer).toHaveBeenCalledWith(9, { rating: "UP", reason: null, comment: null }));
    await waitFor(() => expect(up).toHaveAttribute("aria-pressed", "true"));
    expect(within(panel).getByText(viga.feedback.thanks)).toBeInTheDocument();

    fireEvent.click(up);
    await waitFor(() => expect(api.clearRating).toHaveBeenCalledWith(9));
    await waitFor(() => expect(up).toHaveAttribute("aria-pressed", "false"));
  });

  it("👎 mở lý do chọn nhanh và ghi chú, đều không bắt buộc", async () => {
    api.ask.mockResolvedValue(answered());
    api.rateAnswer.mockResolvedValue({ rating: "DOWN", reason: null, comment: null });
    const panel = renderPanel();
    await ask(panel, "Hồ sơ cần nộp gồm gì?");

    fireEvent.click(await within(panel).findByRole("button", { name: viga.feedback.down }));
    await waitFor(() => expect(api.rateAnswer).toHaveBeenCalledWith(9, { rating: "DOWN", reason: null, comment: null }));

    fireEvent.click(await within(panel).findByRole("button", { name: viga.feedback.reasons.MISSING }));
    await waitFor(() =>
      expect(api.rateAnswer).toHaveBeenLastCalledWith(9, { rating: "DOWN", reason: "MISSING", comment: null }),
    );

    const commentBox = within(panel).getByLabelText(viga.feedback.commentPlaceholder);
    fireEvent.change(commentBox, { target: { value: "Thiếu chứng chỉ" } });
    fireEvent.click(within(commentBox.closest("form") as HTMLElement).getByRole("button", { name: viga.feedback.send }));
    await waitFor(() =>
      expect(api.rateAnswer).toHaveBeenLastCalledWith(9, { rating: "DOWN", reason: "MISSING", comment: "Thiếu chứng chỉ" }),
    );
  });

  it("đánh giá lỗi thì báo và không đổi trạng thái đã chọn", async () => {
    api.ask.mockResolvedValue(answered());
    api.rateAnswer.mockRejectedValue(new VigaError("unavailable"));
    const panel = renderPanel();
    await ask(panel, "Hồ sơ cần nộp gồm gì?");

    const up = await within(panel).findByRole("button", { name: viga.feedback.up });
    fireEvent.click(up);

    expect(await within(panel).findByText(viga.feedback.failed)).toBeInTheDocument();
    expect(up).toHaveAttribute("aria-pressed", "false");
  });

  it("mở lại hội thoại hiện đúng đánh giá đã chọn", async () => {
    const detail = {
      conversation: { id: 3, title: "Giấy tờ ngày đầu", created_at: "2026-10-01T00:00:00Z", updated_at: "2026-10-01T00:00:00Z" },
      messages: [
        message({ id: 1, role: "USER", content: "Hồ sơ?" }),
        message({ id: 2, role: "ASSISTANT", content: "Nộp CV.", response_type: "INFO", feedback: { rating: "DOWN", reason: "WRONG" } }),
      ],
    };
    api.listConversations.mockResolvedValue([detail.conversation]);
    api.getConversation.mockResolvedValue(detail);
    const panel = renderPanel();

    fireEvent.click(within(panel).getByRole("button", { name: viga.history.title }));
    fireEvent.click(await within(panel).findByRole("button", { name: /Giấy tờ ngày đầu/ }));

    const down = await within(panel).findByRole("button", { name: viga.feedback.down });
    expect(down).toHaveAttribute("aria-pressed", "true");
    expect(within(panel).getByRole("button", { name: viga.feedback.reasons.WRONG })).toHaveAttribute("aria-pressed", "true");
  });
});

function message(overrides: Partial<ConversationMessageResponseDTO>): ConversationMessageResponseDTO {
  return {
    id: 1,
    role: "USER",
    content: "",
    response_type: null,
    payload: {},
    created_at: "2026-10-01T00:00:00Z",
    ...overrides,
  };
}

describe("Trang Viga đầy đủ", () => {
  function renderPage() {
    return render(
      <NextIntlClientProvider locale="vi" messages={viMessages}>
        <SessionProvider initialUser={USER}>
          <VigaPage />
        </SessionProvider>
      </NextIntlClientProvider>,
    );
  }

  it("hiện lịch sử bên trái, câu gợi ý ở giữa và hỏi được như ngăn Viga", async () => {
    searchState.value = "";
    api.listConversations.mockResolvedValue([
      { id: 8, title: "Tiến độ", created_at: "2026-10-01T00:00:00Z", updated_at: "2026-10-01T00:00:00Z" },
    ]);
    api.ask.mockResolvedValue(reply({ response_type: "INFO", message: "Mình là Viga." }));
    renderPage();

    expect(await screen.findByRole("button", { name: /Tiến độ/ })).toBeInTheDocument();
    expect(screen.getByText(viga.page.greetingTitle)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: viga.quick.q1 }));
    await waitFor(() => expect(api.ask).toHaveBeenCalledWith({ question: viga.quick.q1, conversation_id: null }));
    expect(await screen.findByText("Mình là Viga.")).toBeInTheDocument();
    // Sau khi hỏi, danh sách bên trái phải nạp lại (cuộc mới/cập nhật) chứ không kẹt ở "Đang tải…".
    await waitFor(() => expect(api.listConversations).toHaveBeenCalledTimes(2));
    expect(screen.queryByText(viga.history.loading)).not.toBeInTheDocument();
  });

  it("mở đúng cuộc trò chuyện được chuyển từ ngăn Viga (?c=)", async () => {
    searchState.value = "c=8";
    api.listConversations.mockResolvedValue([]);
    api.getConversation.mockResolvedValue({
      conversation: { id: 8, title: "Tiến độ", created_at: "2026-10-01T00:00:00Z", updated_at: "2026-10-01T00:00:00Z" },
      messages: [
        message({ id: 1, role: "USER", content: "Tiến độ của tôi?" }),
        message({ id: 2, role: "ASSISTANT", content: "Bạn xong 2/12 việc.", response_type: "INFO" }),
      ],
    });
    renderPage();

    expect(await screen.findByText("Tiến độ của tôi?")).toBeInTheDocument();
    expect(screen.getByText("Bạn xong 2/12 việc.")).toBeInTheDocument();
    expect(api.getConversation).toHaveBeenCalledWith(8);
  });

  it("Enter gửi câu hỏi, Shift+Enter không gửi", async () => {
    searchState.value = "";
    api.listConversations.mockResolvedValue([]);
    api.ask.mockResolvedValue(reply({ response_type: "INFO", message: "ok" }));
    renderPage();

    const input = screen.getByLabelText(viga.inputLabel);
    fireEvent.change(input, { target: { value: "Xin chào" } });
    fireEvent.keyDown(input, { key: "Enter", shiftKey: true });
    expect(api.ask).not.toHaveBeenCalled();

    fireEvent.keyDown(input, { key: "Enter" });
    await waitFor(() => expect(api.ask).toHaveBeenCalledWith({ question: "Xin chào", conversation_id: null }));
  });

  it("nút Thu nhỏ quay về trang chính", async () => {
    searchState.value = "";
    api.listConversations.mockResolvedValue([]);
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: viga.page.collapse }));
    expect(push).toHaveBeenCalledWith("/me");
  });
});

describe("Ngăn Viga có nút Mở rộng", () => {
  it("chuyển sang trang đầy đủ và giữ cuộc trò chuyện đang mở", async () => {
    api.ask.mockResolvedValue(reply({ conversation_id: 12, response_type: "INFO", message: "ok" }));
    const panel = renderPanel();
    await ask(panel, "Xin chào");
    await within(panel).findByText("ok");

    fireEvent.click(within(panel).getByRole("button", { name: viga.expand }));
    expect(push).toHaveBeenCalledWith({ pathname: "/me/viga", query: { c: "12" } });
  });
});

describe("Ngăn Viga đổi được chiều rộng", () => {
  it("mép trái dùng phím mũi tên để rộng hơn hay hẹp lại, nhớ lại lựa chọn và bấm đúp để về mặc định", () => {
    window.localStorage.removeItem("vsf-viga-width");
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1600 }); // đủ rộng để ngăn nới ra được
    const panel = renderPanel();
    const handle = within(panel).getByRole("separator", { name: viga.resize });
    expect(handle).toHaveAttribute("aria-valuenow", "440");

    fireEvent.keyDown(handle, { key: "ArrowLeft" }); // kéo mép sang trái = rộng hơn
    expect(handle).toHaveAttribute("aria-valuenow", "464");
    expect(window.localStorage.getItem("vsf-viga-width")).toBe("464");

    for (let i = 0; i < 40; i++) fireEvent.keyDown(handle, { key: "ArrowRight", shiftKey: true });
    expect(handle).toHaveAttribute("aria-valuenow", "340"); // không hẹp hơn mức tối thiểu

    fireEvent.doubleClick(handle);
    expect(handle).toHaveAttribute("aria-valuenow", "440");
  });
});

describe("Phản hồi Viga của HR", () => {
  const gap = (overrides: Partial<ContentGapResponseDTO>): ContentGapResponseDTO => ({
    id: 1,
    question_text: "Quy định gửi xe máy tầng hầm?",
    occurrences: 3,
    first_asked_at: "2026-09-29T01:00:00Z",
    last_asked_at: "2026-10-01T01:00:00Z",
    resolved: false,
    kind: "NO_BASIS",
    ...overrides,
  });
  const down = (overrides: Partial<DissatisfiedGroupResponseDTO>): DissatisfiedGroupResponseDTO => ({
    id: 5,
    question_text: "Nhận laptop ở đâu?",
    answer_excerpt: "Nhận laptop tại tầng 12.",
    occurrences: 2,
    reasons: ["WRONG"],
    comments: ["Tầng 14 mới đúng"],
    first_at: "2026-09-30T01:00:00Z",
    last_at: "2026-10-02T01:00:00Z",
    resolved: false,
    ...overrides,
  });
  const summary = { up: 8, down: 2, open_down: 2, satisfaction_percent: 80 };

  function setup(gaps: ContentGapResponseDTO[], downs: DissatisfiedGroupResponseDTO[]) {
    api.listContentGaps.mockResolvedValue(gaps);
    api.listDissatisfied.mockResolvedValue(downs);
    api.feedbackSummary.mockResolvedValue(summary);
    return renderHr(<VigaFeedbackPage />);
  }

  it("hiện câu chưa có căn cứ và câu bị 👎 ẩn danh kèm số liệu hài lòng", async () => {
    setup([gap({})], [down({})]);

    expect(await screen.findByText("Quy định gửi xe máy tầng hầm?")).toBeInTheDocument();
    expect(screen.getByText("Nhận laptop ở đâu?")).toBeInTheDocument();
    expect(screen.getByText("80%")).toBeInTheDocument();
    expect(screen.getByText(hrText.feedback.reasons.WRONG)).toBeInTheDocument();
    expect(screen.getByText("Tầng 14 mới đúng")).toBeInTheDocument();
    expect(screen.getByText(/Nhận laptop tại tầng 12/)).toBeInTheDocument();
    expect(screen.getByText(hrText.feedback.privacy)).toBeInTheDocument();
  });

  it("lọc theo loại, tìm không dấu và sắp xếp theo số lần hỏi", async () => {
    setup(
      [gap({ id: 1, occurrences: 1 }), gap({ id: 2, question_text: "Mật khẩu Wi-Fi văn phòng?", occurrences: 6 })],
      [down({})],
    );
    await screen.findByText("Mật khẩu Wi-Fi văn phòng?");

    const titles = () => screen.getAllByRole("listitem").map((item) => within(item).getAllByText(/\?$/)[0]?.textContent);
    expect(titles()).toEqual(["Mật khẩu Wi-Fi văn phòng?", "Nhận laptop ở đâu?", "Quy định gửi xe máy tầng hầm?"]);

    fireEvent.change(screen.getByLabelText(hrText.feedback.kindLabel), { target: { value: "DOWN" } });
    expect(titles()).toEqual(["Nhận laptop ở đâu?"]);

    fireEvent.change(screen.getByLabelText(hrText.feedback.kindLabel), { target: { value: "ALL" } });
    fireEvent.change(screen.getByLabelText(hrText.feedback.searchLabel), { target: { value: "gui xe may" } });
    expect(titles()).toEqual(["Quy định gửi xe máy tầng hầm?"]);

    fireEvent.change(screen.getByLabelText(hrText.feedback.searchLabel), { target: { value: "khong co dong nao" } });
    expect(screen.getByText(hrText.feedback.noMatch)).toBeInTheDocument();
  });

  it("câu đã xử lý chỉ hiện khi đổi trạng thái, kèm tài liệu đã bổ sung", async () => {
    setup([gap({ resolved: true, resolved_document_title: "Hỏi đáp bổ sung" })], []);
    await waitFor(() => expect(api.listContentGaps).toHaveBeenCalled());
    expect(await screen.findByText(hrText.feedback.noMatch)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(hrText.feedback.statusLabel), { target: { value: "resolved" } });
    expect(await screen.findByText("Quy định gửi xe máy tầng hầm?")).toBeInTheDocument();
    expect(screen.getByText("Đã bổ sung ở: Hỏi đáp bổ sung")).toBeInTheDocument();
  });

  it("đánh dấu đã xử lý gọi đúng API theo loại và tải lại", async () => {
    setup([gap({})], [down({})]);
    api.resolveContentGap.mockResolvedValue();
    api.resolveDissatisfied.mockResolvedValue();
    await screen.findByText("Quy định gửi xe máy tầng hầm?");

    const rows = screen.getAllByRole("listitem");
    const gapRow = rows.find((row) => within(row).queryByText("Quy định gửi xe máy tầng hầm?"))!;
    const downRow = rows.find((row) => within(row).queryByText("Nhận laptop ở đâu?"))!;
    fireEvent.click(within(gapRow).getByRole("button", { name: hrText.feedback.resolve }));
    await waitFor(() => expect(api.resolveContentGap).toHaveBeenCalledWith(1));
    fireEvent.click(within(downRow).getByRole("button", { name: hrText.feedback.resolve }));
    await waitFor(() => expect(api.resolveDissatisfied).toHaveBeenCalledWith(5));
    await waitFor(() => expect(api.listContentGaps).toHaveBeenCalledTimes(3));
  });

  it("kiểm tra lại: trả lời được thì hiện đáp án, chưa được thì nhắc viết rõ hơn", async () => {
    setup([gap({})], []);
    api.recheckContentGap
      .mockResolvedValueOnce({ answered: false, message: null, document_title: null, section_heading: null, quote: null, closed: 0 })
      .mockResolvedValueOnce({
        answered: true,
        message: "Gửi xe tại tầng hầm B1.",
        document_title: "Nội quy tòa nhà",
        section_heading: "Gửi xe",
        quote: "tầng hầm B1",
        closed: 1,
      });
    await screen.findByText("Quy định gửi xe máy tầng hầm?");

    fireEvent.click(screen.getByRole("button", { name: hrText.feedback.recheck }));
    expect(await screen.findByText(hrText.feedback.recheckFail)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: hrText.feedback.recheck }));
    expect(await screen.findByText("Gửi xe tại tầng hầm B1.")).toBeInTheDocument();
    expect(api.recheckContentGap).toHaveBeenCalledWith(1);
  });

  it("Bổ sung tài liệu: viết đáp án, chờ cập nhật rồi tự hỏi lại Viga và báo đã trả lời được", async () => {
    setup([gap({})], []);
    api.supplementContentGap.mockResolvedValue({ document_id: 4, document_version_id: 9, version_label: "Bổ sung 1", job_id: 77 });
    api.recheckContentGap.mockResolvedValue({
      answered: true,
      message: "Gửi xe tại tầng hầm B1.",
      document_title: "Hỏi đáp bổ sung",
      section_heading: "Quy định gửi xe máy tầng hầm?",
      quote: "tầng hầm B1",
      closed: 1,
    });
    await screen.findByText("Quy định gửi xe máy tầng hầm?");

    fireEvent.click(screen.getByRole("button", { name: hrText.feedback.addDocument }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByLabelText(hrText.feedback.supplement.question)).toHaveValue("Quy định gửi xe máy tầng hầm?");
    expect(within(dialog).getByRole("button", { name: hrText.feedback.supplement.submit })).toBeDisabled();

    fireEvent.change(within(dialog).getByLabelText(hrText.feedback.supplement.answer), {
      target: { value: "Gửi xe tại tầng hầm B1, quẹt thẻ nhân viên." },
    });
    fireEvent.change(within(dialog).getByLabelText(hrText.feedback.supplement.contact), { target: { value: "Phòng Hành chính" } });
    fireEvent.click(within(dialog).getByRole("button", { name: hrText.feedback.supplement.submit }));

    await waitFor(() =>
      expect(api.supplementContentGap).toHaveBeenCalledWith(1, {
        answer: "Gửi xe tại tầng hầm B1, quẹt thẻ nhân viên.",
        question: "Quy định gửi xe máy tầng hầm?",
        contact: "Phòng Hành chính",
      }),
    );
    expect(await within(dialog).findByText("40%")).toBeInTheDocument();

    await act(async () => jobHooks.done?.({ status: "SUCCEEDED" }));
    expect(await within(dialog).findByText(hrText.feedback.supplement.okTitle)).toBeInTheDocument();
    expect(within(dialog).getByText("Gửi xe tại tầng hầm B1.")).toBeInTheDocument();
    expect(api.recheckContentGap).toHaveBeenCalledWith(1);
  });

  it("câu bị 👎 cũng có nút Bổ sung tài liệu và Kiểm tra lại, gọi đúng API của nhóm 👎", async () => {
    setup([], [down({ id: 5 })]);
    api.supplementDissatisfied.mockResolvedValue({ document_id: 4, document_version_id: 9, version_label: "Bổ sung 1", job_id: 78 });
    api.recheckDissatisfied.mockResolvedValue({ answered: true, message: "Tầng 12.", document_title: "Hỏi đáp bổ sung", section_heading: "Nhận laptop ở đâu?", quote: "tầng 12", closed: 1 });
    await screen.findByText("Nhận laptop ở đâu?");

    expect(screen.getByRole("button", { name: hrText.feedback.recheck })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: hrText.feedback.addDocument }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByLabelText(hrText.feedback.supplement.question)).toHaveValue("Nhận laptop ở đâu?");
    fireEvent.change(within(dialog).getByLabelText(hrText.feedback.supplement.answer), { target: { value: "Nhận laptop tại tầng 12." } });
    fireEvent.click(within(dialog).getByRole("button", { name: hrText.feedback.supplement.submit }));

    await waitFor(() =>
      expect(api.supplementDissatisfied).toHaveBeenCalledWith(5, { answer: "Nhận laptop tại tầng 12.", question: "Nhận laptop ở đâu?", contact: null }),
    );
    await act(async () => jobHooks.done?.({ status: "SUCCEEDED" }));
    expect(await within(dialog).findByText(hrText.feedback.supplement.okTitle)).toBeInTheDocument();
    expect(api.recheckDissatisfied).toHaveBeenCalledWith(5);
    expect(api.supplementContentGap).not.toHaveBeenCalled();
  });

  it("Bổ sung tài liệu: Viga vẫn chưa trả lời được thì cho sửa lại câu trả lời", async () => {
    setup([gap({})], []);
    api.supplementContentGap.mockResolvedValue({ document_id: 4, document_version_id: 9, version_label: "Bổ sung 1", job_id: 77 });
    api.recheckContentGap.mockResolvedValue({ answered: false, message: null, document_title: null, section_heading: null, quote: null, closed: 0 });
    await screen.findByText("Quy định gửi xe máy tầng hầm?");

    fireEvent.click(screen.getByRole("button", { name: hrText.feedback.addDocument }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText(hrText.feedback.supplement.answer), { target: { value: "Câu trả lời mơ hồ." } });
    fireEvent.click(within(dialog).getByRole("button", { name: hrText.feedback.supplement.submit }));
    await waitFor(() => expect(api.supplementContentGap).toHaveBeenCalled());

    await act(async () => jobHooks.done?.({ status: "SUCCEEDED" }));
    expect(await within(dialog).findByText(hrText.feedback.supplement.missTitle)).toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole("button", { name: hrText.feedback.supplement.edit }));
    expect(within(dialog).getByLabelText(hrText.feedback.supplement.answer)).toHaveValue("Câu trả lời mơ hồ.");
  });

  it("Bổ sung tài liệu: việc cập nhật tài liệu lỗi thì báo và cho thử lại", async () => {
    setup([gap({})], []);
    api.supplementContentGap.mockResolvedValue({ document_id: 4, document_version_id: 9, version_label: "Bổ sung 1", job_id: 77 });
    await screen.findByText("Quy định gửi xe máy tầng hầm?");

    fireEvent.click(screen.getByRole("button", { name: hrText.feedback.addDocument }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText(hrText.feedback.supplement.answer), { target: { value: "Gửi xe tại tầng hầm B1." } });
    fireEvent.click(within(dialog).getByRole("button", { name: hrText.feedback.supplement.submit }));
    await waitFor(() => expect(api.supplementContentGap).toHaveBeenCalled());

    await act(async () => jobHooks.done?.({ status: "FAILED" }));
    expect(await within(dialog).findByText(hrText.feedback.supplement.errors.activation)).toBeInTheDocument();
    expect(api.recheckContentGap).not.toHaveBeenCalled();
    expect(within(dialog).getByLabelText(hrText.feedback.supplement.answer)).toHaveValue("Gửi xe tại tầng hầm B1.");
  });
});
