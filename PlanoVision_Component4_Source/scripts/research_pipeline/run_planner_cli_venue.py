"""Venue-input entry point; preserves the frozen historical LKR CLI source."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from component4.planner_input import collect_planner_inputs
from scripts.research_pipeline import run_planner_cli_lkr as legacy


def main():
    dimensions = {}
    def collect(config,event,baseline=None,reader=input,writer=print):
        values,geometry=collect_planner_inputs(config,event,baseline,
            dimensions.get(event),reader,writer)
        dimensions[event]=geometry
        return values
    legacy.collect=collect
    legacy.main()


if __name__=='__main__':
    main()
