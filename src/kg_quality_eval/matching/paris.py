"""Wrapper around the PARIS ontology/instance matcher (dig-team/PARIS v0.3).

PARIS is a holistic, fully unsupervised matcher: it alternates between aligning
instances, relations and classes, using both the graph structure and literal
values, and it needs no training data at all. That makes it the reference point
for our own matchers, and it is the approach the supervisor named explicitly.

It is a Java program without a Python API, so this wrapper

  1. exports both KGs to N-Triples via rdflib (see loaders/rdf_export.py),
  2. runs `java -jar paris.jar <kg1.nt> <kg2.nt> <outdir>`,
  3. reads the entity equivalences of the last completed iteration,
  4. maps the URIs back onto the original OpenEA identifiers.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from pathlib import Path

import pandas as pd

from kg_quality_eval.core import KGPair
from kg_quality_eval.loaders.rdf_export import from_uriref, write_rdf
from kg_quality_eval.matching.base import BaseMatcher, MatchResult

ITERATION_FILE = re.compile(r"^(\d+)_eqv\.tsv$")


class ParisMatcher(BaseMatcher):
    name = "paris"
    family = "holistic"
    requires_seeds = False

    def __init__(
        self,
        jar_path: str | Path = "tools/paris_0_3.jar",
        work_dir: str | Path = "data/processed/paris",
        java_home: str | None = None,
        heap: str = "4g",
        timeout_s: int = 7200,
        keep_work_dir: bool = False,
    ) -> None:
        self.jar_path = Path(jar_path)
        self.work_dir = Path(work_dir)
        self.java_home = java_home or os.environ.get("JAVA_HOME")
        self.heap = heap
        self.timeout_s = timeout_s
        self.keep_work_dir = keep_work_dir

    # -- public API ---------------------------------------------------------

    def match(self, kg_pair: KGPair, seeds: pd.DataFrame | None = None) -> MatchResult:
        start = time.perf_counter()
        run_dir = self.work_dir / kg_pair.name
        out_dir = run_dir / "out"

        if run_dir.exists():
            shutil.rmtree(run_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        nt1, n_triples1 = write_rdf(kg_pair.kg1, run_dir / "kg1.nt", kind="e1")
        nt2, n_triples2 = write_rdf(kg_pair.kg2, run_dir / "kg2.nt", kind="e2")

        log = self._run_paris(nt1, nt2, out_dir)
        pairs, iteration = self._read_output(out_dir)

        # Keep only entity-to-entity equivalences (PARIS also emits relations).
        entities1 = set(kg_pair.kg1.entities["entity_uri"])
        entities2 = set(kg_pair.kg2.entities["entity_uri"])
        pairs = pairs[pairs["e1"].isin(entities1) & pairs["e2"].isin(entities2)]
        pairs = (
            pairs.sort_values("score", ascending=False)
            .drop_duplicates(subset=["e1"])
            .reset_index(drop=True)
        )

        if not self.keep_work_dir:
            for f in (nt1, nt2):
                f.unlink(missing_ok=True)

        return MatchResult(
            matcher=self.name,
            dataset=kg_pair.name,
            pairs=pairs,
            runtime_s=time.perf_counter() - start,
            meta={
                "family": self.family,
                "iteration": iteration,
                "n_triples_exported": (n_triples1, n_triples2),
                "log_tail": log[-500:],
            },
        )

    def available(self) -> tuple[bool, str]:
        """Is PARIS runnable here? Returns (ok, reason)."""
        if not self.jar_path.exists():
            return False, f"jar not found: {self.jar_path}"
        java = self._java()
        if shutil.which(java) is None and not Path(java).exists():
            return False, f"java not found: {java} (set JAVA_HOME)"
        return True, "ok"

    # -- internals ----------------------------------------------------------

    def _java(self) -> str:
        return f"{self.java_home}/bin/java" if self.java_home else "java"

    def _run_paris(self, nt1: Path, nt2: Path, out_dir: Path) -> str:
        cmd = [
            self._java(),
            f"-Xmx{self.heap}",
            "-jar",
            str(self.jar_path),
            str(nt1),
            str(nt2),
            str(out_dir),
        ]
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=self.timeout_s, check=False
        )
        log = (proc.stdout or "") + (proc.stderr or "")
        (out_dir / "paris.log").write_text(log, encoding="utf-8")

        # PARIS writes a progress file into the working directory — move it next
        # to the rest of the run output instead of leaving it in the repo root.
        for stray in Path.cwd().glob("run__*.txt"):
            stray.replace(out_dir / stray.name)

        if not any(ITERATION_FILE.match(p.name) for p in out_dir.iterdir()):
            raise RuntimeError(
                f"PARIS produced no equivalence file (exit {proc.returncode}).\n{log[-2000:]}"
            )
        return log

    def _read_output(self, out_dir: Path) -> tuple[pd.DataFrame, int]:
        """Read the last *non-empty* `<n>_eqv.tsv`, i.e. the converged iteration.

        PARIS always writes one final file for the class-alignment phase that
        contains no entity equivalences, so the highest number is not usable.
        """
        candidates = [
            (int(m.group(1)), p)
            for p in out_dir.iterdir()
            if (m := ITERATION_FILE.match(p.name)) and p.stat().st_size > 0
        ]
        if not candidates:
            raise RuntimeError(f"No non-empty *_eqv.tsv in {out_dir}")

        iteration, path = max(candidates, key=lambda t: t[0])
        df = pd.read_csv(
            path, sep="\t", header=None, names=["e1", "e2", "score"],
            dtype={0: str, 1: str}, na_filter=False, quoting=3,
        )
        df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0.0)
        df["e1"] = [from_uriref(u.strip("<>")) for u in df["e1"]]
        df["e2"] = [from_uriref(u.strip("<>")) for u in df["e2"]]
        return df, iteration
