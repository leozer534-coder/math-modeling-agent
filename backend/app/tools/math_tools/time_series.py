"""
时间序列工具模块 - ARIMA、指数平滑
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np


@dataclass
class ForecastResult:
    """预测结果"""
    forecast: np.ndarray
    confidence_intervals: Optional[np.ndarray] = None
    model_summary: str = ""
    aic: float = float("nan")
    bic: float = float("nan")
    residuals: Optional[np.ndarray] = None


def arima_forecast(
    data: np.ndarray,
    order: Tuple[int, int, int] = (1, 1, 1),
    seasonal_order: Optional[Tuple[int, int, int, int]] = None,
    n_forecast: int = 10,
    alpha: float = 0.05,
) -> ForecastResult:
    """ARIMA / SARIMA 预测

    Args:
        data: 时间序列数据
        order: (p, d, q) ARIMA 阶数
        seasonal_order: (P, D, Q, s) 季节性阶数，None 则不使用
        n_forecast: 预测步数
        alpha: 置信区间显著性水平

    Returns:
        ForecastResult
    """
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    y = np.asarray(data, dtype=float).flatten()

    model = SARIMAX(
        y,
        order=order,
        seasonal_order=seasonal_order or (0, 0, 0, 0),
        enforce_stationarity=False,
        enforce_invertibility=False,
    )
    fitted = model.fit(disp=False)

    forecast_result = fitted.get_forecast(steps=n_forecast, alpha=alpha)
    forecast_values = forecast_result.predicted_mean.values
    ci = forecast_result.conf_int().values

    return ForecastResult(
        forecast=forecast_values,
        confidence_intervals=ci,
        model_summary=str(fitted.summary()),
        aic=fitted.aic,
        bic=fitted.bic,
        residuals=fitted.resid.values,
    )


def exponential_smoothing(
    data: np.ndarray,
    trend: Optional[str] = "add",
    seasonal: Optional[str] = None,
    seasonal_periods: Optional[int] = None,
    n_forecast: int = 10,
) -> ForecastResult:
    """Holt-Winters 指数平滑

    Args:
        data: 时间序列数据
        trend: 趋势成分 "add"/"mul"/None
        seasonal: 季节成分 "add"/"mul"/None
        seasonal_periods: 季节周期
        n_forecast: 预测步数

    Returns:
        ForecastResult
    """
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    y = np.asarray(data, dtype=float).flatten()

    model = ExponentialSmoothing(
        y,
        trend=trend,
        seasonal=seasonal,
        seasonal_periods=seasonal_periods,
    )
    fitted = model.fit(optimized=True)

    forecast_values = fitted.forecast(steps=n_forecast)

    return ForecastResult(
        forecast=np.asarray(forecast_values),
        model_summary=str(fitted.summary()),
        aic=fitted.aic,
        bic=fitted.bic,
        residuals=fitted.resid,
    )
