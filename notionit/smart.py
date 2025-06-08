#!/usr/bin/env python3
"""
스마트 Notion 마크다운 업로더
중복 제목 감지 및 처리, 다양한 전략 지원
"""

import time
import hashlib
import requests
from typing import Optional, List, Dict
from pathlib import Path

from .advanced import AdvancedNotionUploader
from .types import NotionSearchResponse, NotionSearchResultPage, NotionSearchTitleTextObject, UploadResult, UploadStatusResult, DuplicateStrategy


def is_success_result(result: UploadResult) -> bool:
    """결과가 성공적인 API 응답인지 확인"""
    return "id" in result and "status" not in result


def is_status_result(result: UploadResult) -> bool:
    """결과가 상태 결과인지 확인"""
    return "status" in result


class SmartNotionUploader(AdvancedNotionUploader):
    """중복 제목을 방지하는 스마트한 Notion 업로더"""

    def check_existing_pages_with_title(self, title: str) -> List[NotionSearchResultPage]:
        """
        동일한 제목을 가진 기존 페이지들을 검색

        Args:
            title: 검색할 페이지 제목

        Returns:
            동일한 제목을 가진 페이지 리스트
        """
        url = "https://api.notion.com/v1/search"
        search_data = {"query": title, "filter": {"value": "page", "property": "object"}}

        response = requests.post(url, headers=self.headers, json=search_data)
        result: NotionSearchResponse = response.json()

        if "results" in result:
            # 정확한 제목 매치만 필터링
            exact_matches: List[NotionSearchResultPage] = []
            for page in result["results"]:
                if "properties" in page and "title" in page["properties"]:
                    page_title_array: List[NotionSearchTitleTextObject] = page["properties"]["title"]["title"]
                    if page_title_array:
                        page_title: str = page_title_array[0]["text"]["content"]
                        if page_title == title:
                            exact_matches.append(page)
            return exact_matches

        return []

    def generate_unique_title(self, base_title: str, strategy: str = "timestamp") -> str:
        """
        고유한 제목 생성

        Args:
            base_title: 기본 제목
            strategy: 고유화 전략 ("timestamp", "counter", "hash")

        Returns:
            고유한 제목
        """
        if strategy == "timestamp":
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            return f"{base_title} ({timestamp})"

        elif strategy == "counter":
            existing_pages = self.check_existing_pages_with_title(base_title)
            if not existing_pages:
                return base_title

            counter = 1
            while True:
                new_title = f"{base_title} ({counter})"
                if not self.check_existing_pages_with_title(new_title):
                    return new_title
                counter += 1

        elif strategy == "hash":
            # 파일 내용 기반 해시
            file_hash = hashlib.md5(base_title.encode()).hexdigest()[:8]
            return f"{base_title} ({file_hash})"

        return base_title

    def smart_upload_markdown_file(
        self,
        file_path: str,
        parent_page_id: str,
        page_title: Optional[str] = None,
        duplicate_strategy: DuplicateStrategy = "ask",
    ) -> UploadResult:
        """
        스마트한 마크다운 파일 업로드

        Args:
            file_path: 마크다운 파일 경로
            parent_page_id: 부모 페이지 ID
            page_title: 페이지 제목 (None이면 파일명 사용)
            duplicate_strategy: 중복 처리 전략

        Returns:
            업로드 결과 (성공 응답 또는 상태)
        """
        path = Path(file_path)

        if page_title is None:
            page_title = path.stem

        # 기존 페이지 확인
        existing_pages = self.check_existing_pages_with_title(page_title)

        if existing_pages:
            if self.debug:
                print(f"⚠️  동일한 제목 '{page_title}'을 가진 페이지가 {len(existing_pages)}개 존재합니다.")

            if duplicate_strategy == "ask":
                print(f"⚠️  동일한 제목 '{page_title}'을 가진 페이지가 {len(existing_pages)}개 존재합니다.")
                print("어떻게 처리하시겠습니까?")
                print("1. 타임스탬프 추가하여 새 페이지 생성")
                print("2. 번호 추가하여 새 페이지 생성")
                print("3. 기존 페이지 무시하고 새 페이지 생성")
                print("4. 업로드 취소")

                choice = input("선택 (1-4): ").strip()
                if choice == "1":
                    duplicate_strategy = "timestamp"
                elif choice == "2":
                    duplicate_strategy = "counter"
                elif choice == "3":
                    duplicate_strategy = "create_anyway"
                else:
                    print("❌ 업로드가 취소되었습니다.")
                    return {"status": "cancelled"}

            if duplicate_strategy == "timestamp":
                page_title = self.generate_unique_title(page_title, "timestamp")
                if self.debug:
                    print(f"📝 새 제목: {page_title}")

            elif duplicate_strategy == "counter":
                page_title = self.generate_unique_title(page_title, "counter")
                if self.debug:
                    print(f"📝 새 제목: {page_title}")

            elif duplicate_strategy == "skip":
                if self.debug:
                    print("⏭️  업로드를 건너뜁니다.")
                return {"status": "skipped"}

        # 일반 업로드 진행
        result = self.upload_markdown_file(file_path, parent_page_id, page_title)
        return result

    def batch_upload_files(
        self,
        file_paths: List[str],
        parent_page_id: str,
        duplicate_strategy: DuplicateStrategy = "timestamp",
        delay_seconds: float = 1.0,
    ) -> List[UploadResult]:
        """
        여러 파일을 일괄 업로드

        Args:
            file_paths: 업로드할 파일 경로 리스트
            parent_page_id: 부모 페이지 ID
            duplicate_strategy: 중복 처리 전략
            delay_seconds: 파일 간 지연 시간 (초)

        Returns:
            업로드 결과 리스트
        """
        results: List[UploadResult] = []

        for i, file_path in enumerate(file_paths):
            if self.debug:
                print(f"\n📁 {i + 1}/{len(file_paths)}: {file_path}")

            try:
                result = self.smart_upload_markdown_file(file_path, parent_page_id, duplicate_strategy=duplicate_strategy)
                results.append(result)

                if is_success_result(result):
                    if self.debug:
                        print(f"✅ 업로드 성공: {result.get('id', '')}")
                else:
                    if self.debug:
                        print(f"⚠️  업로드 결과: {result.get('status', 'unknown')}")

            except Exception as e:
                if self.debug:
                    print(f"❌ 업로드 실패: {e}")
                # 에러를 상태 결과로 변환
                error_result: UploadStatusResult = {"status": "cancelled"}
                results.append(error_result)

            # 다음 파일 업로드 전 지연
            if i < len(file_paths) - 1 and delay_seconds > 0:
                time.sleep(delay_seconds)

        return results

    def get_upload_summary(self, results: List[UploadResult]) -> Dict[str, int]:
        """
        업로드 결과 요약 생성

        Args:
            results: 업로드 결과 리스트

        Returns:
            결과 요약 딕셔너리
        """
        summary = {"total": len(results), "success": 0, "cancelled": 0, "skipped": 0, "failed": 0}

        for result in results:
            if is_success_result(result):
                summary["success"] += 1
            elif is_status_result(result):
                status = result.get("status", "failed")
                if status == "cancelled":
                    summary["cancelled"] += 1
                elif status == "skipped":
                    summary["skipped"] += 1
                else:
                    summary["failed"] += 1
            else:
                summary["failed"] += 1

        return summary

    def print_upload_summary(self, results: List[UploadResult]) -> None:
        """업로드 결과 요약 출력"""
        summary = self.get_upload_summary(results)

        print("\n📊 업로드 결과 요약:")
        print(f"  전체: {summary['total']}개")
        print(f"  성공: {summary['success']}개 ✅")
        print(f"  취소: {summary['cancelled']}개 ❌")
        print(f"  건너뜀: {summary['skipped']}개 ⏭️")
        print(f"  실패: {summary['failed']}개 🚫")

        success_rate = (summary["success"] / summary["total"] * 100) if summary["total"] > 0 else 0
        print(f"  성공률: {success_rate:.1f}%")
