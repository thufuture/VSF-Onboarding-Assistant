/** Bỏ dấu và đưa về chữ thường để tìm "thu" ra cả "Thư"; `đ` không tách được bằng NFD nên đổi riêng. */
export function foldText(text: string): string {
  return text
    .toLowerCase() // trước khi đổi `đ`: chữ `Đ` hoa cũng phải ra `d`
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/đ/g, "d");
}
