"""
Report generation for backtest results.

Generates HTML reports with interactive charts, metrics tables,
and performance analysis.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Union

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from jinja2 import Template


class ReportGenerator:
    """Generate HTML reports for backtest results."""

    HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SignalOps Report - {{ strategy_name }}</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        :root {
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent: #3b82f6;
            --success: #22c55e;
            --warning: #eab308;
            --danger: #ef4444;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 2rem; }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--bg-secondary);
        }
        h1 { font-size: 1.5rem; font-weight: 600; }
        .timestamp { color: var(--text-secondary); font-size: 0.875rem; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
        .card {
            background: var(--bg-secondary);
            border-radius: 0.5rem;
            padding: 1.25rem;
        }
        .card-label { color: var(--text-secondary); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }
        .card-value { font-size: 1.5rem; font-weight: 600; margin-top: 0.25rem; }
        .card-value.positive { color: var(--success); }
        .card-value.negative { color: var(--danger); }
        .card-value.warning { color: var(--warning); }
        .chart-container { background: var(--bg-secondary); border-radius: 0.5rem; padding: 1rem; margin-bottom: 2rem; }
        .chart-title { font-size: 1rem; font-weight: 600; margin-bottom: 1rem; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 0.75rem; text-align: left; border-bottom: 1px solid var(--bg-primary); }
        th { color: var(--text-secondary); font-weight: 500; font-size: 0.75rem; text-transform: uppercase; }
        .section { margin-bottom: 2rem; }
        .section-title { font-size: 1.125rem; font-weight: 600; margin-bottom: 1rem; }
        .badge {
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            font-size: 0.75rem;
            font-weight: 500;
        }
        .badge-success { background: rgba(34, 197, 94, 0.2); color: var(--success); }
        .badge-warning { background: rgba(234, 179, 8, 0.2); color: var(--warning); }
        .badge-danger { background: rgba(239, 68, 68, 0.2); color: var(--danger); }
        .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; }
        @media (max-width: 768px) { .two-col { grid-template-columns: 1fr; } }
        .footer { margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--bg-secondary); color: var(--text-secondary); font-size: 0.875rem; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{{ strategy_name }}</h1>
            <span class="timestamp">Generated: {{ timestamp }}</span>
        </header>

        <div class="grid">
            <div class="card">
                <div class="card-label">Total Return</div>
                <div class="card-value {{ 'positive' if total_return > 0 else 'negative' }}">
                    {{ "%.2f"|format(total_return * 100) }}%
                </div>
            </div>
            <div class="card">
                <div class="card-label">Sharpe Ratio</div>
                <div class="card-value {{ 'positive' if sharpe > 1 else 'warning' if sharpe > 0 else 'negative' }}">
                    {{ "%.2f"|format(sharpe) }}
                </div>
            </div>
            <div class="card">
                <div class="card-label">Max Drawdown</div>
                <div class="card-value {{ 'positive' if max_drawdown < 0.1 else 'warning' if max_drawdown < 0.2 else 'negative' }}">
                    {{ "%.2f"|format(max_drawdown * 100) }}%
                </div>
            </div>
            <div class="card">
                <div class="card-label">Win Rate</div>
                <div class="card-value {{ 'positive' if win_rate > 0.5 else 'warning' }}">
                    {{ "%.1f"|format(win_rate * 100) }}%
                </div>
            </div>
            <div class="card">
                <div class="card-label">CAGR</div>
                <div class="card-value {{ 'positive' if cagr > 0 else 'negative' }}">
                    {{ "%.2f"|format(cagr * 100) }}%
                </div>
            </div>
            <div class="card">
                <div class="card-label">Sortino Ratio</div>
                <div class="card-value {{ 'positive' if sortino > 1 else 'warning' if sortino > 0 else 'negative' }}">
                    {{ "%.2f"|format(sortino) }}
                </div>
            </div>
        </div>

        {% if overfit_warning %}
        <div class="card" style="background: rgba(239, 68, 68, 0.1); border: 1px solid var(--danger); margin-bottom: 2rem;">
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <span class="badge badge-danger">Warning</span>
                <span>Potential overfitting detected. Review the analysis below.</span>
            </div>
        </div>
        {% endif %}

        <div class="chart-container">
            <div class="chart-title">Equity Curve</div>
            <div id="equity-chart"></div>
        </div>

        <div class="two-col">
            <div class="chart-container">
                <div class="chart-title">Drawdown</div>
                <div id="drawdown-chart"></div>
            </div>
            <div class="chart-container">
                <div class="chart-title">Monthly Returns</div>
                <div id="returns-chart"></div>
            </div>
        </div>

        {% if train_metrics and test_metrics %}
        <div class="section">
            <div class="section-title">Train vs Test Comparison</div>
            <div class="card">
                <table>
                    <thead>
                        <tr>
                            <th>Metric</th>
                            <th>In-Sample (Train)</th>
                            <th>Out-of-Sample (Test)</th>
                            <th>Degradation</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for metric in comparison_metrics %}
                        <tr>
                            <td>{{ metric.name }}</td>
                            <td>{{ metric.train }}</td>
                            <td>{{ metric.test }}</td>
                            <td>
                                {% if metric.degradation %}
                                <span class="badge {{ 'badge-danger' if metric.degradation > 20 else 'badge-warning' if metric.degradation > 10 else 'badge-success' }}">
                                    {{ metric.degradation }}%
                                </span>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        {% endif %}

        <div class="section">
            <div class="section-title">Strategy Configuration</div>
            <div class="card">
                <table>
                    <tbody>
                        {% for key, value in config.items() %}
                        <tr>
                            <td style="color: var(--text-secondary);">{{ key }}</td>
                            <td>{{ value }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="footer">
            <p>SignalOps - Paper Trading Research Platform</p>
            <p>This report is for research purposes only. Not financial advice.</p>
        </div>
    </div>

    <script>
        const chartConfig = { responsive: true, displayModeBar: false };
        const layout = {
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { color: '#94a3b8' },
            margin: { t: 20, r: 20, b: 40, l: 60 },
            xaxis: { gridcolor: '#1e293b', linecolor: '#1e293b' },
            yaxis: { gridcolor: '#1e293b', linecolor: '#1e293b' }
        };

        // Equity Chart
        Plotly.newPlot('equity-chart', [{
            x: {{ equity_dates | tojson }},
            y: {{ equity_values | tojson }},
            type: 'scatter',
            mode: 'lines',
            line: { color: '#3b82f6', width: 2 },
            fill: 'tozeroy',
            fillcolor: 'rgba(59, 130, 246, 0.1)'
        }], {...layout, height: 300}, chartConfig);

        // Drawdown Chart
        Plotly.newPlot('drawdown-chart', [{
            x: {{ drawdown_dates | tojson }},
            y: {{ drawdown_values | tojson }},
            type: 'scatter',
            mode: 'lines',
            line: { color: '#ef4444', width: 2 },
            fill: 'tozeroy',
            fillcolor: 'rgba(239, 68, 68, 0.1)'
        }], {...layout, height: 250}, chartConfig);

        // Monthly Returns Chart
        Plotly.newPlot('returns-chart', [{
            x: {{ monthly_dates | tojson }},
            y: {{ monthly_returns | tojson }},
            type: 'bar',
            marker: {
                color: {{ monthly_returns | tojson }}.map(v => v >= 0 ? '#22c55e' : '#ef4444')
            }
        }], {...layout, height: 250}, chartConfig);
    </script>
</body>
</html>
    """

    def __init__(self):
        """Initialize report generator."""
        self.template = Template(self.HTML_TEMPLATE)

    def generate(
        self,
        result: Any,  # BacktestResult
        output_path: Optional[Union[str, Path]] = None,
    ) -> str:
        """Generate HTML report from backtest result.

        Args:
            result: BacktestResult object
            output_path: Optional path to save HTML file

        Returns:
            HTML string
        """
        # Extract data for charts
        equity_dates = [str(d) for d in result.equity_curve.index]
        equity_values = result.equity_curve.tolist()

        # Calculate drawdown series
        rolling_max = result.equity_curve.expanding().max()
        drawdown = (result.equity_curve - rolling_max) / rolling_max
        drawdown_dates = [str(d) for d in drawdown.index]
        drawdown_values = (drawdown * 100).tolist()  # As percentage

        # Monthly returns
        try:
            monthly = result.returns.resample("ME").sum()
        except Exception:
            try:
                monthly = result.returns.resample("M").sum()
            except Exception:
                monthly = result.returns.groupby(pd.Grouper(freq="ME")).sum()
        monthly_dates = [str(d) for d in monthly.index]
        monthly_returns = (monthly * 100).tolist()

        # Prepare comparison metrics
        comparison_metrics = []
        if result.train_metrics and result.test_metrics:
            for metric in ["sharpe", "sortino", "max_drawdown", "cagr", "win_rate"]:
                train_val = result.train_metrics.get(metric, 0)
                test_val = result.test_metrics.get(metric, 0)

                # Calculate degradation
                if train_val != 0:
                    if metric == "max_drawdown":
                        # For drawdown, higher is worse
                        degradation = ((test_val - train_val) / train_val) * 100
                    else:
                        degradation = ((train_val - test_val) / abs(train_val)) * 100
                else:
                    degradation = 0

                comparison_metrics.append({
                    "name": metric.replace("_", " ").title(),
                    "train": f"{train_val:.2f}" if isinstance(train_val, float) else str(train_val),
                    "test": f"{test_val:.2f}" if isinstance(test_val, float) else str(test_val),
                    "degradation": round(degradation) if degradation > 0 else None,
                })

        # Check for overfit warning
        overfit_warning = False
        if result.train_metrics and result.test_metrics:
            train_sharpe = result.train_metrics.get("sharpe", 0)
            test_sharpe = result.test_metrics.get("sharpe", 0)
            if train_sharpe > 0 and (train_sharpe - test_sharpe) / train_sharpe > 0.3:
                overfit_warning = True

        # Render template
        html = self.template.render(
            strategy_name=result.strategy_name,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            total_return=result.metrics.get("total_return", 0),
            sharpe=result.metrics.get("sharpe", 0),
            max_drawdown=result.metrics.get("max_drawdown", 0),
            win_rate=result.metrics.get("win_rate", 0),
            cagr=result.metrics.get("cagr", 0),
            sortino=result.metrics.get("sortino", 0),
            equity_dates=equity_dates,
            equity_values=equity_values,
            drawdown_dates=drawdown_dates,
            drawdown_values=drawdown_values,
            monthly_dates=monthly_dates,
            monthly_returns=monthly_returns,
            train_metrics=result.train_metrics,
            test_metrics=result.test_metrics,
            comparison_metrics=comparison_metrics,
            overfit_warning=overfit_warning,
            config=result.config or {},
        )

        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                f.write(html)

        return html

    def generate_summary_json(self, result: Any) -> dict:
        """Generate JSON summary for API responses.

        Args:
            result: BacktestResult object

        Returns:
            Summary dictionary
        """
        return {
            "strategy": result.strategy_name,
            "generated_at": datetime.now().isoformat(),
            "metrics": {
                "full_period": result.metrics,
                "train": result.train_metrics,
                "test": result.test_metrics,
            },
            "period": {
                "start": str(result.returns.index.min()) if len(result.returns) > 0 else None,
                "end": str(result.returns.index.max()) if len(result.returns) > 0 else None,
                "train_end": result.train_end_date,
                "test_start": result.test_start_date,
            },
            "config": result.config,
        }
