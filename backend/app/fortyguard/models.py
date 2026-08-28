from typing import Literal, Optional

from pydantic import BaseModel, Field

AnalyticType = Literal["tcm", "time_of_measure", "exceedance", "persistence"]
Granularity = Literal[60, 80, 100]
FilterType = Literal[1, 2, 3, 4, 5]


class DateTimeSpec(BaseModel):
    start_date: str = Field(description="Date to analyze, YYYY-MM-DD. 2021-01-01 to today (+12h for heatmap forecasts).")
    start_time: str = Field(description="Time of day, HH:MM (24h). Heat varies enormously by hour.")
    filter_type: FilterType = Field(
        default=1,
        description="1=single hour, 2=range of hours (needs end_time), 3=entire day, 4=range of days, 5=single month.",
    )
    end_time: Optional[str] = Field(default=None, description="Required when filter_type=2 (range of hours), HH:MM.")
    end_date: Optional[str] = Field(default=None, description="Required when filter_type=4 (range of days), YYYY-MM-DD.")


class PolygonAOI(BaseModel):
    """GeoJSON FeatureCollection containing a single Polygon. Coordinates are [longitude, latitude];
    the first and last point of the ring must match to close it. U.S. locations only."""

    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[dict] = Field(description="Exactly one Feature with a Polygon geometry.")


class HeatmapRequest(BaseModel):
    polygon_aoi: PolygonAOI
    date_time: DateTimeSpec
    granularity: Granularity = Field(default=100, description="Output grid detail in meters: 60, 80, or 100. Smaller = finer + more credit cost.")
    analytic_type: Optional[AnalyticType] = Field(
        default=None,
        description="tcm=raw temperature, time_of_measure=snapshot, exceedance=threshold breach analysis, persistence=how long heat lingers.",
    )


class PointSpec(BaseModel):
    lat: float = Field(description="Latitude of the point, U.S. locations only.")
    lon: float = Field(description="Longitude of the point.")


class EnvParamsRequest(BaseModel):
    point: PointSpec
    date_time: DateTimeSpec


class StatusResult(BaseModel):
    status: str
    result: Optional[dict] = None
    raw: dict = Field(default_factory=dict, exclude=True)


class UsageResult(BaseModel):
    total_available_credits: Optional[int] = None
    cycle_credits_used: Optional[int] = None
    cycle_remaining_credits: Optional[int] = None
    raw: dict = Field(default_factory=dict)
