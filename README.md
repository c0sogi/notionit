# Notion Markdown Uploader

마크다운 파일을 Notion 페이지로 변환하고 업로드하는 Python 패키지

## ✨ 주요 기능

- 📝 **완전한 마크다운 지원**: 헤더, 단락, 인라인/블록 수식
- 💻 **코드 블록 지원**: 60+ 프로그래밍 언어 자동 감지
- 🧮 **수식 정리**: LaTeX 수식 자동 최적화 및 Notion 호환성 보장
- 🔄 **중복 제목 처리**: 다양한 전략으로 중복 제목 자동 처리
- 📦 **일괄 업로드**: 여러 파일을 한 번에 업로드
- 🛡️ **타입 안전성**: 완전한 타입 힌팅 및 mypy 호환

## 🚀 빠른 시작

### 설치

```bash
# requirements.txt 의존성 설치
pip install -r notion_md_uploader/requirements.txt
```

### 기본 사용법

```python
from notion_md_uploader import SmartNotionUploader

# 업로더 생성
uploader = SmartNotionUploader(
    token="your_notion_token",
    debug=True  # 디버깅 출력 활성화
)

# 마크다운 파일 업로드
result = uploader.smart_upload_markdown_file(
    file_path="document.md",
    parent_page_id="your_parent_page_id",
    page_title="My Document",  # 선택사항
    duplicate_strategy="timestamp"  # 중복 처리 전략
)

# 결과 확인
if "id" in result:
    print(f"✅ 업로드 성공! 페이지 ID: {result['id']}")
    print(f"🔗 URL: https://www.notion.so/{result['id'].replace('-', '')}")
else:
    print(f"❌ 업로드 실패: {result}")
```

### 편의 함수 사용

```python
from notion_md_uploader import quick_upload

# 한 줄로 업로드
result = quick_upload(
    token="your_notion_token",
    file_path="document.md",
    parent_page_id="your_parent_page_id",
    duplicate_strategy="counter"
)
```

## 🎯 고급 사용법

### 중복 제목 처리 전략

```python
# 1. 타임스탬프 추가 (기본값)
uploader.smart_upload_markdown_file(
    "file.md", 
    parent_id,
    duplicate_strategy="timestamp"  # "제목 (20241208_143022)"
)

# 2. 번호 추가
uploader.smart_upload_markdown_file(
    "file.md", 
    parent_id,
    duplicate_strategy="counter"  # "제목 (1)", "제목 (2)" ...
)

# 3. 사용자에게 묻기
uploader.smart_upload_markdown_file(
    "file.md", 
    parent_id,
    duplicate_strategy="ask"  # 터미널에서 선택 메뉴 출력
)

# 4. 무시하고 생성
uploader.smart_upload_markdown_file(
    "file.md", 
    parent_id,
    duplicate_strategy="create_anyway"  # 동일 제목이어도 생성
)

# 5. 건너뛰기
uploader.smart_upload_markdown_file(
    "file.md", 
    parent_id,
    duplicate_strategy="skip"  # 중복 시 업로드 취소
)
```

### 일괄 업로드

```python
# 여러 파일을 한 번에 업로드
files = ["doc1.md", "doc2.md", "doc3.md"]

results = uploader.batch_upload_files(
    file_paths=files,
    parent_page_id="parent_id",
    duplicate_strategy="timestamp",
    delay_seconds=2.0  # 파일 간 지연 시간
)

# 결과 요약 출력
uploader.print_upload_summary(results)
```

### 디버깅 모드

```python
# 상세한 디버깅 정보 출력
uploader = SmartNotionUploader(token, debug=True)

# 파싱 과정 상세 출력:
# 🔍 마크다운 파싱 시작...
#   라인 1: ## 제목
#     📝 헤더 (레벨 2): 제목
#   라인 3: 수식이 포함된 단락 $E=mc^2$
#     📄 단락: 수식이 포함된 단락 $E=mc^2$
#     💫 인라인 수식 포함
```

## 📚 지원하는 마크다운 요소

### ✅ 완전 지원
- **헤더**: `# H1`, `## H2`, `### H3`
- **단락**: 일반 텍스트 및 인라인 수식
- **수식**: 
  - 인라인: `$E=mc^2$`
  - 블록: `$$\int_0^\infty e^{-x} dx = 1$$`
- **코드 블록**: 
  ```python
  def hello():
      print("Hello, World!")
  ```

### 🚧 향후 지원 예정
- **서식**: `**굵게**`, `*기울임*`
- **리스트**: 순서 있는/없는 리스트
- **링크**: `[텍스트](URL)`
- **이미지**: `![alt](image.png)`

## 🔧 API 참조

### SmartNotionUploader

가장 고급 기능을 제공하는 메인 클래스

#### 메서드

- `smart_upload_markdown_file()`: 스마트 업로드 (중복 처리 포함)
- `batch_upload_files()`: 일괄 업로드
- `check_existing_pages_with_title()`: 제목 중복 검사
- `generate_unique_title()`: 고유 제목 생성

### AdvancedNotionUploader

코드 블록과 수식 정리 기능 제공

#### 메서드

- `upload_markdown_file()`: 기본 업로드
- `parse_markdown_to_blocks()`: 마크다운 파싱

### NotionMarkdownUploader

기본적인 마크다운 업로드 기능

#### 메서드

- `upload_markdown_file()`: 기본 업로드
- `create_page()`: 페이지 생성

## 🛠️ 개발자 가이드

### 타입 체크

```bash
# mypy를 사용한 타입 체크
mypy notion_md_uploader/
```

### 지원 언어

코드 블록에서 자동 감지되는 언어들:

- **메이저 언어**: Python, JavaScript, TypeScript, Java, C++, Go, Rust
- **웹 기술**: HTML, CSS, SCSS, JSON, XML
- **데이터베이스**: SQL
- **설정 파일**: YAML, TOML, INI
- **기타**: 60+ 언어 지원

### 에러 처리

```python
from notion_md_uploader import is_success_result, is_status_result

result = uploader.smart_upload_markdown_file(...)

if is_success_result(result):
    print(f"성공: {result['id']}")
elif is_status_result(result):
    print(f"상태: {result['status']}")  # cancelled, skipped
else:
    print(f"오류: {result}")
```

## 📄 라이센스

MIT License

## 🤝 기여하기

1. Fork the repository
2. Create your feature branch
3. Add type hints and tests
4. Submit a pull request

## 🐛 버그 리포트

문제가 발생하면 다음 정보와 함께 이슈를 생성해주세요:

- Python 버전
- 패키지 버전
- 에러 메시지
- 최소 재현 코드

---

**Happy Notion-ing!** 🚀 