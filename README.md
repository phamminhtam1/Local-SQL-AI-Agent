# Trợ lý AI MySQL

Ứng dụng Streamlit cung cấp giao diện AI để truy vấn cơ sở dữ liệu MySQL bằng ngôn ngữ tự nhiên.

## Tính năng

- Chuyển đổi ngôn ngữ tự nhiên sang SQL sử dụng mô hình OpenAI GPT
- Thực thi SQL an toàn (chỉ truy vấn SELECT)
- Khám phá schema cơ sở dữ liệu
- Giao diện web Streamlit tương tác

## Yêu cầu

- Docker và Docker Compose
- Khóa API OpenAI

## Khởi động nhanh với Docker

### 1. Clone và Thiết lập

```bash
git clone <your-repo>
cd <your-repo>
```

### 2. Cấu hình Môi trường

Sao chép file môi trường mẫu và thêm khóa API OpenAI của bạn:

```bash
cp env.example .env
```

Chỉnh sửa file `.env` và thêm khóa API OpenAI của bạn:

```
OPENAI_API_KEY=your_actual_openai_api_key_here
```

### 3. Chạy với Docker Compose

```bash
# Khởi động ứng dụng với cơ sở dữ liệu MySQL
docker-compose up -d

# Xem logs
docker-compose logs -f streamlit
```

### 4. Truy cập Ứng dụng Streamlit

Mở trình duyệt và truy cập: http://localhost:8501

Giao diện Streamlit cung cấp:

- Trò chuyện tương tác với cơ sở dữ liệu
- Hiển thị schema cơ sở dữ liệu
- Theo dõi lịch sử truy vấn
- Trực quan hóa truy vấn SQL
- Kết quả trong bảng tương tác

## Build Docker Thủ công

Nếu bạn muốn build thủ công:

```bash
# Build Docker image
docker build -t mysql-ai-agent .

# Chạy container (đảm bảo MySQL đang chạy riêng biệt)
docker run -p 8501:8501 \
  -e OPENAI_API_KEY=your_api_key \
  -e DB_URI=mysql+pymysql://user:password@host:3306/database \
  -e STREAMLIT_SERVER_PORT=8501 \
  -e STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
  streamlit-agent
```

## Phát triển

### Thiết lập Phát triển Cục bộ

1. Cài đặt các phụ thuộc Python:

```bash
pip install -r requirements.txt
```

2. Thiết lập biến môi trường:

```bash
cp env.example .env
# Chỉnh sửa .env với các giá trị thực tế của bạn
```

3. Chạy ứng dụng Streamlit:

```bash
# Tùy chọn 1: Sử dụng script khởi động
python run_streamlit.py

# Tùy chọn 2: Lệnh streamlit trực tiếp
streamlit run streamlit_app.py
```

## Cấu hình

### Biến Môi trường

- `OPENAI_API_KEY`: Khóa API OpenAI của bạn (bắt buộc)
- `OPENAI_MODEL`: Mô hình OpenAI để sử dụng (mặc định: gpt-4o-mini)
- `DB_URI`: Chuỗi kết nối cơ sở dữ liệu MySQL

### Kết nối Cơ sở dữ liệu

Ứng dụng yêu cầu cơ sở dữ liệu MySQL. Bạn có thể:

1. Sử dụng container MySQL có sẵn trong docker-compose.yml
2. Kết nối với instance MySQL hiện có
3. Sử dụng dịch vụ MySQL trên cloud

## Sử dụng

1. Mở giao diện web tại http://localhost:8501
2. Hỏi câu hỏi về cơ sở dữ liệu của bạn bằng ngôn ngữ tự nhiên
3. AI sẽ chuyển đổi câu hỏi của bạn thành SQL và thực thi một cách an toàn

### Tính năng

- **Giao diện Trò chuyện Tương tác**: Trò chuyện ngôn ngữ tự nhiên với cơ sở dữ liệu
- **Hiển thị Schema Cơ sở dữ liệu**: Xem cấu trúc cơ sở dữ liệu trong thanh bên
- **Lịch sử Truy vấn**: Theo dõi tất cả truy vấn và kết quả trước đó
- **Hiển thị Truy vấn SQL**: Xem các truy vấn SQL được tạo
- **Trực quan hóa Kết quả**: Xem kết quả truy vấn trong bảng
- **Phản hồi Thông minh**: Xử lý cả truy vấn cơ sở dữ liệu và câu hỏi chung

### Ví dụ Truy vấn

- "Hiển thị tất cả người dùng"
- "Có bao nhiêu đơn hàng?"
- "Kể cho tôi nghe một câu chuyện cười" (cho câu hỏi không liên quan đến cơ sở dữ liệu)
- "Sản phẩm nào phổ biến nhất?"
- "Liệt kê người dùng được tạo trong tháng trước"

## Bảo mật

- Chỉ cho phép truy vấn SELECT
- Không cho phép các thao tác ghi (INSERT, UPDATE, DELETE)
- Thông tin đăng nhập cơ sở dữ liệu phải được bảo mật

## Khắc phục sự cố

### Vấn đề Thường gặp

1. **Lỗi Kết nối Cơ sở dữ liệu**: Kiểm tra DB_URI và đảm bảo MySQL đang chạy
2. **Lỗi API OpenAI**: Xác minh khóa API của bạn chính xác và có đủ tín dụng
3. **Cổng Đã được Sử dụng**: Thay đổi cổng trong docker-compose.yml hoặc dừng các dịch vụ khác

### Logs

```bash
# Xem logs ứng dụng
docker-compose logs app

# Xem logs cơ sở dữ liệu
docker-compose logs mysql
```

## Dừng Ứng dụng

```bash
# Dừng tất cả dịch vụ
docker-compose down

# Dừng và xóa volumes (CẢNH BÁO: Điều này sẽ xóa dữ liệu cơ sở dữ liệu của bạn)
docker-compose down -v
```
