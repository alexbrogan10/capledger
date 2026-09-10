"""Tests for the Phase 5 contract-value ML model. Verifies the training
pipeline runs, produces a sane evaluation metric, and that predictions are
explainable and reproducible — not that it predicts any specific real-world
value (the training data is synthetic; see docs/ml_documentation.md)."""
from app.ml.contract_value_model import train_contract_value_model


class TestContractValueModel:
    def test_training_produces_metadata(self, db_session):
        model = train_contract_value_model(db_session)
        assert model.metadata.dataset_size > 100
        assert model.metadata.train_size + model.metadata.test_size == model.metadata.dataset_size
        assert "QB" in model.metadata.positions_seen

    def test_prediction_is_nonnegative_and_explainable(self, db_session):
        model = train_contract_value_model(db_session)
        result = model.predict(position="QB", age=27, contract_length_years=3)
        assert result.predicted_aav >= 0
        assert len(result.drivers) == 3

    def test_qb_predicted_higher_than_long_snapper(self, db_session):
        # A sanity check that the model learned the position hierarchy
        # baked into the synthetic data generator (QB >> LS in AAV).
        model = train_contract_value_model(db_session)
        qb = model.predict(position="QB", age=27, contract_length_years=3)
        ls = model.predict(position="LS", age=27, contract_length_years=3)
        assert qb.predicted_aav > ls.predicted_aav

    def test_deterministic_given_same_data(self, db_session):
        model_a = train_contract_value_model(db_session)
        model_b = train_contract_value_model(db_session)
        pred_a = model_a.predict("WR", 27, 3)
        pred_b = model_b.predict("WR", 27, 3)
        assert pred_a.predicted_aav == pred_b.predicted_aav

    def test_raises_with_too_little_data(self, db_session):
        import pytest
        from unittest.mock import patch
        import pandas as pd

        with patch("app.ml.contract_value_model._load_training_frame", return_value=pd.DataFrame()):
            with pytest.raises(ValueError):
                train_contract_value_model(db_session)
