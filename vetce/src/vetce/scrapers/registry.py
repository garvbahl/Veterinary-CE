"""Central registry of all scraper classes, keyed by source slug.

This is the single source of truth for "every scraper we have". The scheduler,
the run-all orchestrator, and any tooling should import SCRAPER_REGISTRY from
here rather than maintaining their own partial lists.

When you add a new scraper: add one line to SCRAPER_REGISTRY below.
"""
from __future__ import annotations

from typing import Type

from vetce.scrapers.base import BaseScraper
from vetce.scrapers.sites.adtc_courses import AdtcCoursesScraper
from vetce.scrapers.sites.avdc_events import AvdcEventsScraper
from vetce.scrapers.sites.canvas_catalog import TuftsVetCEScraper
from vetce.scrapers.sites.cornell_cvm import CornellCvmScraper
from vetce.scrapers.sites.crown_vet_dentistry import CrownVetDentistryScraper
from vetce.scrapers.sites.illinois_dentistry import IllinoisDentistryScraper
from vetce.scrapers.sites.navta import NavtaScraper
from vetce.scrapers.sites.periovive_thinkific import PerioviveThinkificScraper
from vetce.scrapers.sites.periovive_webinars import PerioviveWebinarsScraper
from vetce.scrapers.sites.vdspets import VdsPetsScraper
from vetce.scrapers.sites.vetandtech_webinars import VetAndTechWebinarsScraper
from vetce.scrapers.sites.vetdentalclasses import VetDentalClassesScraper
from vetce.scrapers.sites.vetfolio_catalog import VetfolioCatalogScraper
from vetce.scrapers.sites.vetmedteam import VetMedTeamScraper
from vetce.scrapers.sites.vetvine import VetVineScraper

# source.slug -> scraper class.
# Every scraper we run automatically must be listed here.
SCRAPER_REGISTRY: dict[str, Type[BaseScraper]] = {
    AdtcCoursesScraper.SOURCE_SLUG: AdtcCoursesScraper,
    AvdcEventsScraper.SOURCE_SLUG: AvdcEventsScraper,
    TuftsVetCEScraper.SOURCE_SLUG: TuftsVetCEScraper,
    CornellCvmScraper.SOURCE_SLUG: CornellCvmScraper,
    CrownVetDentistryScraper.SOURCE_SLUG: CrownVetDentistryScraper,
    IllinoisDentistryScraper.SOURCE_SLUG: IllinoisDentistryScraper,
    NavtaScraper.SOURCE_SLUG: NavtaScraper,
    PerioviveThinkificScraper.SOURCE_SLUG: PerioviveThinkificScraper,
    PerioviveWebinarsScraper.SOURCE_SLUG: PerioviveWebinarsScraper,
    VdsPetsScraper.SOURCE_SLUG: VdsPetsScraper,
    VetAndTechWebinarsScraper.SOURCE_SLUG: VetAndTechWebinarsScraper,
    VetDentalClassesScraper.SOURCE_SLUG: VetDentalClassesScraper,
    VetfolioCatalogScraper.SOURCE_SLUG: VetfolioCatalogScraper,
    VetMedTeamScraper.SOURCE_SLUG: VetMedTeamScraper,
    VetVineScraper.SOURCE_SLUG: VetVineScraper,
}