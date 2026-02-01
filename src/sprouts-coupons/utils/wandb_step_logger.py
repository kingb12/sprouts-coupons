import logging
import pprint
from typing import Any


def mark_run_complete(run: Any | None = None):
    """
    Sets the `complete_run` tag on the given run, or the current one if called from a context that is already logging
    to `wandb` and passes no `run` argument
    """
    try:
        import wandb  # type: ignore

        if not run:
            run = wandb.Api().run(f"{wandb.run.entity}/{wandb.run.project}/{wandb.run.id}")
        run.tags.append("complete_run")
        run.update()
    except ImportError as e:
        logging.warning("wandb not installed, cannot mark run as complete! Doing nothing.", exc_info=e)


class WandbStepLogger:
    """A logger that logs items in lock-step to wandb, allowing one to easily log partial information across code
    before incrementing `current_step` with step() and logging all the information at once.
    """

    current_step: int
    log_for_step: dict[str, Any]

    def __init__(self) -> None:
        super().__init__()
        self.current_step = 0
        self.log_for_step = {}

    def log(self, items: dict[str, Any]) -> None:
        self.log_for_step.update(items)

    def step(self, increment: int = 1) -> None:
        try:
            import wandb

            if wandb.run is not None:
                wandb.log({"current_step": self.current_step, **self.log_for_step})
            else:
                if self.current_step == 0:
                    logging.warning("WANDB NOT INITIALIZED! print-logging anything sent to WandbSteplLogger")
                pprint.pprint({"current_step": self.current_step, **self.log_for_step})
        except ImportError:
            if self.current_step == 0:
                logging.warning("wandb not installed, cannot log! print-logging anything sent to WandbSteplLogger")
            pprint.pprint({"current_step": self.current_step, **self.log_for_step})

        self.current_step += increment
        self.log_for_step = {}
