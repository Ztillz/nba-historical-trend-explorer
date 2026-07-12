from __future__ import annotations

import logging
import random
import time
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import leaguegamelog


VALID_SEASON_TYPES = {
    "Regular Season",
    "Playoffs",
}


class LeagueGameLogClient:
    """
    Client responsible for downloading and caching team-level NBA game logs.

    The client separates API ingestion from transformation logic. Raw endpoint
    output is stored before any columns are renamed or calculations are made.
    """

    def __init__(
        self,
        raw_data_directory: Path,
        logger: logging.Logger,
        timeout_seconds: int = 60,
        max_retries: int = 4,
        base_retry_delay_seconds: float = 5.0,
    ) -> None:
        self.raw_data_directory = raw_data_directory
        self.logger = logger
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.base_retry_delay_seconds = base_retry_delay_seconds

        self.raw_data_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def get_team_game_logs(
        self,
        season: str,
        season_type: str,
        force_refresh: bool = False,
    ) -> pd.DataFrame:
        """
        Return team-level game logs for one season and season type.

        The method first checks for a locally cached CSV. If the file exists,
        it is loaded instead of calling the NBA API unless force_refresh=True.
        """
        self._validate_inputs(
            season=season,
            season_type=season_type,
        )

        raw_file = self._build_raw_file_path(
            season=season,
            season_type=season_type,
        )

        if raw_file.exists() and not force_refresh:
            self.logger.info(
                "Loading cached raw game log: %s",
                raw_file,
            )

            return self._read_cached_csv(raw_file)

        dataframe = self._download_with_retries(
            season=season,
            season_type=season_type,
        )

        if dataframe.empty:
            raise ValueError(
                f"NBA API returned zero rows for "
                f"{season} {season_type}."
            )

        dataframe.to_csv(
            raw_file,
            index=False,
        )

        self.logger.info(
            "Saved %s raw rows to %s",
            f"{len(dataframe):,}",
            raw_file,
        )

        return dataframe

    def _download_with_retries(
        self,
        season: str,
        season_type: str,
    ) -> pd.DataFrame:
        """
        Call LeagueGameLog with retry and exponential-backoff logic.
        """
        last_exception: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                self.logger.info(
                    "Downloading %s %s team game logs. Attempt %s of %s.",
                    season,
                    season_type,
                    attempt,
                    self.max_retries,
                )

                response = leaguegamelog.LeagueGameLog(
                    season=season,
                    season_type_all_star=season_type,
                    player_or_team_abbreviation="T",
                    sorter="DATE",
                    direction="ASC",
                    timeout=self.timeout_seconds,
                )

                data_frames = response.get_data_frames()

                if not data_frames:
                    raise ValueError(
                        "LeagueGameLog response contained no datasets."
                    )

                dataframe = data_frames[0].copy()

                self.logger.info(
                    "NBA API returned %s rows and %s columns.",
                    f"{len(dataframe):,}",
                    len(dataframe.columns),
                )

                return dataframe

            except Exception as exc:
                last_exception = exc

                self.logger.warning(
                    "Request failed on attempt %s: %s",
                    attempt,
                    exc,
                )

                if attempt == self.max_retries:
                    break

                exponential_delay = (
                    self.base_retry_delay_seconds
                    * (2 ** (attempt - 1))
                )

                jitter = random.uniform(0.5, 2.0)
                sleep_seconds = exponential_delay + jitter

                self.logger.info(
                    "Retrying after %.1f seconds.",
                    sleep_seconds,
                )

                time.sleep(sleep_seconds)

        raise RuntimeError(
            f"Unable to download {season} {season_type} "
            f"after {self.max_retries} attempts."
        ) from last_exception

    def _build_raw_file_path(
        self,
        season: str,
        season_type: str,
    ) -> Path:
        """
        Build a consistent cache filename.
        """
        season_type_slug = (
            season_type.lower()
            .replace(" ", "_")
        )

        season_directory = (
            self.raw_data_directory
            / season_type_slug
        )

        season_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        return season_directory / f"{season}.csv"

    @staticmethod
    def _read_cached_csv(raw_file: Path) -> pd.DataFrame:
        """
        Read cached data while preserving GAME_ID as a string.

        NBA game IDs may begin with zero, so they should never be treated
        as integers.
        """
        return pd.read_csv(
            raw_file,
            dtype={
                "GAME_ID": "string",
                "TEAM_ID": "int64",
            },
        )

    @staticmethod
    def _validate_inputs(
        season: str,
        season_type: str,
    ) -> None:
        """
        Validate season formatting and supported season types.
        """
        if not isinstance(season, str):
            raise TypeError("season must be a string such as '2023-24'.")

        if len(season) != 7 or season[4] != "-":
            raise ValueError(
                "season must use the NBA format YYYY-YY, "
                "for example '2023-24'."
            )

        start_year_text, end_year_text = season.split("-")

        if not start_year_text.isdigit() or not end_year_text.isdigit():
            raise ValueError(
                "season must contain numeric years, "
                "for example '2023-24'."
            )

        expected_end_year = (int(start_year_text) + 1) % 100

        if int(end_year_text) != expected_end_year:
            raise ValueError(
                f"Invalid season value {season}. "
                f"Expected {start_year_text}-{expected_end_year:02d}."
            )

        if season_type not in VALID_SEASON_TYPES:
            raise ValueError(
                f"Unsupported season type: {season_type}. "
                f"Expected one of {sorted(VALID_SEASON_TYPES)}."
            )