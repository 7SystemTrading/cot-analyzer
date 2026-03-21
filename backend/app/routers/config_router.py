from fastapi import APIRouter
from app.schemas import BiasThresholdsIn, ConfigOut, ScoreWeightsIn
import app.config as cfg

router = APIRouter(prefix="/api/v1/config", tags=["config"])

# Runtime-muuttujat (ei persist tietokantaan v1:ssä)
_current_weights = ScoreWeightsIn(
    w_a=cfg.DEFAULT_WEIGHTS.w_a,
    w_b=cfg.DEFAULT_WEIGHTS.w_b,
    w_c=cfg.DEFAULT_WEIGHTS.w_c,
    w_d=cfg.DEFAULT_WEIGHTS.w_d,
)
_current_thresholds = BiasThresholdsIn(
    currency_strong_bull=cfg.DEFAULT_CURRENCY_THRESHOLDS.strong_bull,
    currency_mild_bull=cfg.DEFAULT_CURRENCY_THRESHOLDS.mild_bull,
    currency_mild_bear=cfg.DEFAULT_CURRENCY_THRESHOLDS.mild_bear,
    currency_strong_bear=cfg.DEFAULT_CURRENCY_THRESHOLDS.strong_bear,
    pair_exceptional_bull=cfg.DEFAULT_PAIR_THRESHOLDS.exceptional_bull_score,
    pair_strong_bull=cfg.DEFAULT_PAIR_THRESHOLDS.strong_bull,
    pair_mild_bull=cfg.DEFAULT_PAIR_THRESHOLDS.mild_bull,
    pair_mild_bear=cfg.DEFAULT_PAIR_THRESHOLDS.mild_bear,
    pair_strong_bear=cfg.DEFAULT_PAIR_THRESHOLDS.strong_bear,
    pair_exceptional_bear=cfg.DEFAULT_PAIR_THRESHOLDS.exceptional_bear_score,
)


@router.get("", response_model=ConfigOut)
def get_config():
    """Palauttaa nykyiset laskentapainot ja kynnysarvot."""
    return ConfigOut(weights=_current_weights, thresholds=_current_thresholds)


@router.put("/weights", response_model=ScoreWeightsIn)
def update_weights(weights: ScoreWeightsIn):
    """Päivittää CurrencyScore-painot."""
    total = weights.w_a + weights.w_b + weights.w_c + weights.w_d
    if abs(total - 1.0) > 0.001:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Painojen summan on oltava 1.0, nyt {total:.3f}",
        )
    global _current_weights
    _current_weights = weights
    # Päivitä myös runtime-config
    cfg.DEFAULT_WEIGHTS.w_a = weights.w_a
    cfg.DEFAULT_WEIGHTS.w_b = weights.w_b
    cfg.DEFAULT_WEIGHTS.w_c = weights.w_c
    cfg.DEFAULT_WEIGHTS.w_d = weights.w_d
    return _current_weights


@router.put("/thresholds", response_model=BiasThresholdsIn)
def update_thresholds(thresholds: BiasThresholdsIn):
    """Päivittää bias-kynnysarvot."""
    global _current_thresholds
    _current_thresholds = thresholds
    cfg.DEFAULT_CURRENCY_THRESHOLDS.strong_bull = thresholds.currency_strong_bull
    cfg.DEFAULT_CURRENCY_THRESHOLDS.mild_bull = thresholds.currency_mild_bull
    cfg.DEFAULT_CURRENCY_THRESHOLDS.mild_bear = thresholds.currency_mild_bear
    cfg.DEFAULT_CURRENCY_THRESHOLDS.strong_bear = thresholds.currency_strong_bear
    cfg.DEFAULT_PAIR_THRESHOLDS.exceptional_bull_score = thresholds.pair_exceptional_bull
    cfg.DEFAULT_PAIR_THRESHOLDS.strong_bull = thresholds.pair_strong_bull
    cfg.DEFAULT_PAIR_THRESHOLDS.mild_bull = thresholds.pair_mild_bull
    cfg.DEFAULT_PAIR_THRESHOLDS.mild_bear = thresholds.pair_mild_bear
    cfg.DEFAULT_PAIR_THRESHOLDS.strong_bear = thresholds.pair_strong_bear
    cfg.DEFAULT_PAIR_THRESHOLDS.exceptional_bear_score = thresholds.pair_exceptional_bear
    return _current_thresholds
