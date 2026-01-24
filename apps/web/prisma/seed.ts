import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

const sampleStrategies = [
  {
    name: "MA Crossover SPY",
    description: "Simple moving average crossover strategy on SPY ETF. Goes long when 10-day MA crosses above 30-day MA.",
    code: `"""
Moving Average Crossover Strategy
"""
import pandas as pd

def generate_signals(prices, config):
    fast = prices['close'].rolling(config['fast_window']).mean()
    slow = prices['close'].rolling(config['slow_window']).mean()
    signals = pd.Series(0, index=prices.index)
    signals[fast > slow] = 1
    signals[fast < slow] = -1
    return signals
`,
    config: JSON.stringify({
      fast_window: 10,
      slow_window: 30,
      ticker: "SPY",
      start_date: "2020-01-01",
      end_date: "2023-12-31",
    }),
  },
  {
    name: "Triple MA Trend",
    description: "Triple moving average trend-following strategy. Uses 5/20/50 day MAs for trend confirmation.",
    code: `"""
Triple Moving Average Strategy
"""
import pandas as pd

def generate_signals(prices, config):
    fast = prices['close'].rolling(5).mean()
    medium = prices['close'].rolling(20).mean()
    slow = prices['close'].rolling(50).mean()
    signals = pd.Series(0, index=prices.index)
    signals[(fast > medium) & (medium > slow)] = 1
    signals[(fast < medium) & (medium < slow)] = -1
    return signals
`,
    config: JSON.stringify({
      ticker: "QQQ",
      start_date: "2020-01-01",
      end_date: "2023-12-31",
    }),
  },
  {
    name: "Mean Reversion RSI",
    description: "Mean reversion strategy using RSI. Buys oversold conditions, sells overbought.",
    code: `"""
RSI Mean Reversion Strategy
"""
import pandas as pd
import numpy as np

def generate_signals(prices, config):
    delta = prices['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    signals = pd.Series(0, index=prices.index)
    signals[rsi < 30] = 1   # Oversold - buy
    signals[rsi > 70] = -1  # Overbought - sell
    return signals
`,
    config: JSON.stringify({
      ticker: "AAPL",
      start_date: "2020-01-01",
      end_date: "2023-12-31",
      rsi_period: 14,
      oversold: 30,
      overbought: 70,
    }),
  },
];

async function main() {
  console.log("Seeding database...");

  for (const strategy of sampleStrategies) {
    const existing = await prisma.strategy.findFirst({
      where: { name: strategy.name },
    });

    if (!existing) {
      const created = await prisma.strategy.create({
        data: strategy,
      });
      console.log(`Created strategy: ${created.name}`);

      // Create a sample completed run for the first strategy
      if (strategy.name === "MA Crossover SPY") {
        await prisma.run.create({
          data: {
            strategyId: created.id,
            status: "completed",
            config: strategy.config,
            metrics: JSON.stringify({
              sharpe: 1.24,
              sortino: 1.87,
              total_return: 0.342,
              max_drawdown: 0.156,
              cagr: 0.089,
              win_rate: 0.54,
            }),
            startedAt: new Date(Date.now() - 3600000),
            completedAt: new Date(),
          },
        });
        console.log(`Created sample run for: ${created.name}`);
      }
    } else {
      console.log(`Strategy already exists: ${strategy.name}`);
    }
  }

  console.log("Seeding complete!");
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
