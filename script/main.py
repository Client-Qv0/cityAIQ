"""城市天气质量数据分析与预测入口"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from analysis.main import run

if __name__ == '__main__':
    run()
