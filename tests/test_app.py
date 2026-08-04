import unittest
from unittest.mock import patch

import app


class ApiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.app.config.update(TESTING=True)
        cls.client = app.app.test_client()

    def test_health_is_machine_readable_and_has_security_headers(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body['status'], 'healthy')
        self.assertIn(body['market_data'], {'live-only', 'fallback-enabled'})
        self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
        self.assertIn('ready', body)
        self.assertIn('X-Request-ID', response.headers)

    def test_untrusted_request_id_is_replaced_with_safe_id(self):
        response = self.client.get('/health', headers={'X-Request-ID': 'not a safe id'})
        self.assertRegex(response.headers['X-Request-ID'], r'^[a-f0-9]{16}$')

    def test_production_mutations_fail_closed_without_admin_token(self):
        original_testing = app.app.config.get('TESTING')
        try:
            app.app.config['TESTING'] = False
            with patch.object(app, 'APP_ENV', 'production'), patch.object(app, 'ADMIN_API_TOKEN', ''):
                response = self.client.post('/api/trading-sim/reset')
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.get_json()['code'], 'admin_not_configured')
                readiness = self.client.get('/ready')
                self.assertEqual(readiness.status_code, 503)
                self.assertEqual(readiness.get_json()['status'], 'not_ready')
        finally:
            app.app.config['TESTING'] = original_testing

    def test_analyze_requires_valid_json_and_ticker(self):
        self.assertEqual(self.client.post('/api/analyze').status_code, 400)
        response = self.client.post('/api/analyze', json={'ticker': 'AAPL/../../secret'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()['code'], 'invalid_ticker')

    def test_screen_validates_filter_and_limit(self):
        self.assertEqual(self.client.get('/api/screen?filter=made_up').status_code, 400)
        self.assertEqual(self.client.get('/api/screen?limit=0').status_code, 400)
        self.assertEqual(self.client.get('/api/screen?limit=abc').status_code, 400)

    def test_admin_token_protects_mutating_simulation_routes(self):
        with patch.object(app, 'ADMIN_API_TOKEN', 'test-secret'):
            response = self.client.post('/api/trading-sim/reset')
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.get_json()['code'], 'forbidden')
            response = self.client.post('/api/trading-sim/manual-trade', json={})
            self.assertEqual(response.status_code, 403)

    def test_admin_token_allows_authenticated_reset(self):
        with patch.object(app, 'ADMIN_API_TOKEN', 'test-secret'):
            response = self.client.post(
                '/api/trading-sim/reset',
                headers={'X-Admin-Token': 'test-secret'},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json()['status'], 'success')

    def test_manual_trade_rejects_bad_quantity_without_mutation(self):
        before = app.trading_sim.get_status()['num_trades']
        response = self.client.post(
            '/api/trading-sim/manual-trade',
            json={'type': 'buy', 'ticker': 'AAPL', 'quantity': 'not-a-number'},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()['code'], 'invalid_quantity')
        self.assertEqual(app.trading_sim.get_status()['num_trades'], before)

    @patch.object(app, 'get_market_indexes', return_value=[])
    @patch.object(app, 'get_fast_market_sentiment', return_value={'vix': 18})
    @patch.object(
        app,
        'get_quick_stock_data',
        return_value=[
            {
                'ticker': 'AAPL',
                'company_name': 'Apple',
                'current_price': 100,
                'price': 100,
                'change_pct': 2.5,
                'source': 'test-provider',
                'stale': False,
                'as_of': '2026-08-04T00:00:00',
            }
        ],
    )
    def test_snapshot_labels_momentum_without_inventing_score(self, _stocks, _sentiment, _indexes):
        response = self.client.get('/api/snapshot')
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body['data_status'], 'partial')
        self.assertEqual(body['leaders'][0]['signal_basis'], 'one_day_change')
        self.assertNotIn('score', body['leaders'][0])

    @patch.object(app, 'get_quick_stock_data', return_value=[])
    @patch.object(app, 'get_fast_market_sentiment', return_value={'data_status': 'unavailable'})
    @patch.object(app, 'get_market_indexes', side_effect=RuntimeError('provider down'))
    def test_snapshot_failure_is_not_labeled_live(self, _indexes, _sentiment, _stocks):
        response = self.client.get('/api/snapshot')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()['data_mode'], 'unavailable')

    def test_fallback_index_data_is_labeled_fallback(self):
        indexes = [{
            'symbol': 'SPY',
            'name': 'SPY',
            'price': 100,
            'change': 1,
            'change_pct': 1,
            'source': 'configured_fallback',
            'stale': True,
            'as_of': None,
        }]
        with patch.object(app, 'get_market_indexes', return_value=indexes):
            response = self.client.get('/api/market-indexes')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['data_status'], 'fallback')
        self.assertEqual(response.get_json()['data_mode'], 'fallback')

    def test_unavailable_index_data_does_not_claim_live_mode(self):
        indexes = [{
            'symbol': 'SPY',
            'name': 'SPY',
            'price': None,
            'change': None,
            'change_pct': None,
            'source': 'unavailable',
            'stale': False,
            'as_of': None,
        }]
        with patch.object(app, 'get_market_indexes', return_value=indexes):
            response = self.client.get('/api/market-indexes')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['data_status'], 'unavailable')
        self.assertEqual(response.get_json()['data_mode'], 'unavailable')


class SimulatorInvariantTests(unittest.TestCase):
    def setUp(self):
        self.sim = app.TradingSimulator()

    def test_conflicting_positions_are_rejected(self):
        self.assertEqual(self.sim.execute_trade('buy', 'AAPL', 10, 100, 'test')['status'], 'executed')
        conflict = self.sim.execute_trade('short', 'AAPL', 1, 100, 'test')
        self.assertEqual(conflict['status'], 'rejected')
        self.assertEqual(len(self.sim.positions), 1)

        self.assertEqual(self.sim.execute_trade('sell', 'AAPL', 10, 100, 'test')['status'], 'executed')
        self.assertEqual(self.sim.execute_trade('short', 'AAPL', 10, 100, 'test')['status'], 'executed')
        conflict = self.sim.execute_trade('buy', 'AAPL', 1, 100, 'test')
        self.assertEqual(conflict['status'], 'rejected')

    def test_non_finite_trade_values_are_rejected(self):
        result = self.sim.execute_trade('buy', 'AAPL', float('nan'), 100, 'test')
        self.assertEqual(result['status'], 'rejected')
        self.assertEqual(self.sim.trade_log, [])

    def test_unpriced_positions_are_exposed_as_unavailable(self):
        self.assertEqual(self.sim.execute_trade('buy', 'AAPL', 10, 100, 'test')['status'], 'executed')
        with patch.object(app, 'get_cached_history', return_value=app.pd.DataFrame()):
            status = self.sim.get_status()
        self.assertIsNone(status['total_value'])
        self.assertEqual(status['data_status'], 'unavailable')
        self.assertIsNone(status['positions'][0]['current_price'])

    def test_missing_benchmark_is_not_reported_as_flat_return(self):
        with patch.object(self.sim, 'get_current_price', return_value=None):
            status = self.sim.get_status()
        self.assertEqual(status['data_status'], 'live')
        self.assertEqual(status['benchmark_status'], 'unavailable')
        self.assertIsNone(status['spy_return'])
        self.assertIsNone(status['alpha'])

    def test_initial_snapshot_marks_lazy_benchmark_when_loaded(self):
        with patch.object(self.sim, 'get_current_price', return_value=100.0):
            self.sim.get_status()
        self.assertEqual(self.sim.portfolio_history[0]['benchmark_status'], 'live')
        self.assertEqual(self.sim.portfolio_history[0]['spy_price'], 100.0)


class DataModeTests(unittest.TestCase):
    def test_fallback_is_explicitly_opt_in(self):
        app.clear_cache()
        with patch.object(app, 'get_stooq_quote', return_value=None), patch.object(
            app, 'ALLOW_FALLBACK_MARKET_DATA', False
        ):
            self.assertIsNone(app.get_quote_with_fallback('AAPL'))

        app.clear_cache()
        with patch.object(app, 'get_stooq_quote', return_value=None), patch.object(
            app, 'ALLOW_FALLBACK_MARKET_DATA', True
        ):
            quote = app.get_quote_with_fallback('AAPL')
            self.assertEqual(quote['source'], 'configured_fallback')
            self.assertTrue(quote['stale'])

    def test_quote_with_invalid_previous_close_preserves_missing_change(self):
        frame = app.pd.DataFrame({'Close': [0.0, 100.0]})
        with patch.object(app, 'get_stooq_data', return_value=frame):
            quote = app.get_stooq_quote('AAPL')
        self.assertEqual(quote['price'], 100.0)
        self.assertIsNone(quote['change'])
        self.assertIsNone(quote['change_pct'])


class ProviderAvailabilityTests(unittest.TestCase):
    def test_dividend_yield_normalizes_provider_ratio_or_percent(self):
        self.assertEqual(app._as_dividend_percentage({'dividendYield': 0.0036}), 0.36)
        self.assertEqual(app._as_dividend_percentage({'dividendYield': 0.36}), 0.36)
        self.assertIsNone(app._as_dividend_percentage({'dividendYield': None}))

    def test_consumer_proxy_failure_is_unavailable_not_neutral(self):
        with patch.object(app, 'get_cached_history', return_value=app.pd.DataFrame()):
            sentiment = app.get_consumer_sentiment()
        self.assertEqual(sentiment['data_status'], 'unavailable')
        self.assertEqual(sentiment['consumer_signal'], 'UNAVAILABLE')
        self.assertIsNone(sentiment['retail_sentiment'])

    def test_fast_vix_change_preserves_missing_provider_value(self):
        with patch.object(
            app,
            'get_quote_with_fallback',
            side_effect=[
                {'price': 18.0, 'change_pct': None, 'stale': False},
                None,
            ],
            ):
            sentiment = app.get_fast_market_sentiment()
        self.assertEqual(sentiment['data_status'], 'partial')
        self.assertIsNone(sentiment['vix_change'])

    def test_market_sentiment_is_partial_when_auxiliary_provider_is_missing(self):
        vix_history = app.pd.DataFrame({'Close': [18.0, 19.0]})
        with patch.object(
            app,
            'get_cached_history',
            side_effect=[vix_history, app.pd.DataFrame(), app.pd.DataFrame()],
        ):
            sentiment = app.get_market_sentiment()
        self.assertEqual(sentiment['data_status'], 'partial')
        self.assertEqual(sentiment['vix'], 19.0)
        self.assertNotIn('treasury_10y', sentiment)

    def test_snapshot_watchlist_skips_quote_without_daily_change(self):
        with patch.object(
            app,
            'get_quote_with_fallback',
            return_value={'price': 123.45, 'change_pct': None, 'stale': False},
        ):
            self.assertEqual(app.get_quick_stock_data(['AAPL']), [])

    def test_screener_preserves_missing_company_metadata(self):
        result = {
            'ticker': 'AAPL',
            'company_name': 'Apple',
            'sector': 'Technology',
            'industry': 'Hardware',
            'score': 50,
            'recommendation': 'HOLD',
            'current_price': 100,
            'indicators': {'RSI': None},
            'confidence': 'LOW',
        }
        with patch.object(app, 'SCREENING_UNIVERSE', ['AAPL']), patch.object(
            app, 'calculate_investment_score', return_value=result
        ), patch.object(app, 'get_cached_info', return_value={}):
            stocks = app.screen_stocks('all', 1)
        self.assertEqual(len(stocks), 1)
        self.assertIsNone(stocks[0]['market_cap'])
        self.assertEqual(stocks[0]['size_category'], 'Unknown')
        self.assertIsNone(stocks[0]['employees'])
        self.assertIsNone(stocks[0]['country'])
        self.assertIsNone(stocks[0]['rsi'])


if __name__ == '__main__':
    unittest.main()
