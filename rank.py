"""
Main Ranking Module - Entry Point
Reads candidates from gzipped JSONL, scores them, and outputs ranked CSV.
"""

import gzip
import json
import csv
import sys
import time
from typing import List, Tuple
from scorer import CandidateScorer


def load_candidates(filepath: str) -> List[dict]:
    """
    Load candidates from gzipped JSONL file.
    
    Args:
        filepath: Path to candidates.jsonl.gz
        
    Returns:
        List of candidate dictionaries
    """
    candidates = []
    
    try:
        with gzip.open(filepath, 'rt', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    candidate = json.loads(line.strip())
                    candidates.append(candidate)
                except json.JSONDecodeError as e:
                    print(f"Warning: Failed to parse JSON at line {line_num}: {e}", file=sys.stderr)
                    continue
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)
    
    return candidates


def rank_candidates(candidates: List[dict], scorer: CandidateScorer) -> List[Tuple[str, int, float, str]]:
    """
    Score and rank all candidates.
    
    Args:
        candidates: List of candidate dictionaries
        scorer: CandidateScorer instance
        
    Returns:
        List of tuples: (candidate_id, rank, score, reasoning)
    """
    scored_candidates = []
    
    print(f"Scoring {len(candidates)} candidates...", file=sys.stderr)
    start_time = time.time()
    
    for idx, candidate in enumerate(candidates):
        if idx % 10000 == 0 and idx > 0:
            elapsed = time.time() - start_time
            rate = idx / elapsed
            remaining = (len(candidates) - idx) / rate if rate > 0 else 0
            print(f"  Processed {idx}/{len(candidates)} ({rate:.0f} cand/sec, "
                  f"~{remaining:.0f}s remaining)", file=sys.stderr)
        
        candidate_id = candidate.get('candidate_id', f'UNKNOWN_{idx}')
        score, reasoning = scorer.score(candidate)
        
        scored_candidates.append({
            'candidate_id': candidate_id,
            'score': score,
            'reasoning': reasoning,
            'candidate': candidate
        })
    
    elapsed = time.time() - start_time
    rate = len(candidates) / elapsed if elapsed > 0 else 0
    print(f"Completed scoring in {elapsed:.1f}s ({rate:.0f} candidates/sec)", file=sys.stderr)
    
    # Sort by score descending
    scored_candidates.sort(key=lambda x: x['score'], reverse=True)
    
    # Take top 100 and assign ranks
    top_100 = scored_candidates[:100]
    ranked_results = [
        (item['candidate_id'], rank, item['score'], item['reasoning'])
        for rank, item in enumerate(top_100, 1)
    ]
    
    return ranked_results


def write_output(ranked_results: List[Tuple[str, int, float, str]], output_filepath: str):
    """
    Write ranked results to CSV.
    
    Args:
        ranked_results: List of ranked candidate tuples
        output_filepath: Output CSV file path
    """
    try:
        with open(output_filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow(['candidate_id', 'rank', 'score', 'reasoning'])
            
            # Write data rows
            for candidate_id, rank, score, reasoning in ranked_results:
                writer.writerow([candidate_id, rank, f'{score:.6f}', reasoning])
        
        print(f"Results written to {output_filepath}", file=sys.stderr)
    except Exception as e:
        print(f"Error writing output: {e}", file=sys.stderr)
        sys.exit(1)


def validate_output(ranked_results: List[Tuple[str, int, float, str]]) -> bool:
    """
    Validate output format and constraints.
    
    Args:
        ranked_results: List of ranked candidate tuples
        
    Returns:
        True if valid, False otherwise
    """
    errors = []
    
    # Check count
    if len(ranked_results) != 100:
        errors.append(f"Expected 100 candidates, got {len(ranked_results)}")
    
    # Check ranks are 1-100
    ranks = [r[1] for r in ranked_results]
    if ranks != list(range(1, 101)):
        errors.append("Ranks must be exactly 1-100, each appearing once")
    
    # Check scores are non-increasing
    scores = [r[2] for r in ranked_results]
    for i in range(1, len(scores)):
        if scores[i] > scores[i-1] + 1e-9:  # Small epsilon for floating point
            errors.append(f"Scores not non-increasing: {scores[i-1]} -> {scores[i]}")
            break
    
    # Check no duplicate candidate IDs
    ids = [r[0] for r in ranked_results]
    if len(ids) != len(set(ids)):
        errors.append("Duplicate candidate IDs found")
    
    # Check all scores are in valid range
    for score in scores:
        if score < 0.0 or score > 1.0:
            errors.append(f"Score out of range [0,1]: {score}")
            break
    
    # Report errors
    if errors:
        print("Validation Errors:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return False
    
    print("✓ Output validation passed", file=sys.stderr)
    return True


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Rank candidates for Senior AI Engineer role at Redrob AI'
    )
    parser.add_argument(
        'input_file',
        help='Input gzipped JSONL file (candidates.jsonl.gz)'
    )
    parser.add_argument(
        '-o', '--output',
        default='ranked_candidates.csv',
        help='Output CSV file (default: ranked_candidates.csv)'
    )
    parser.add_argument(
        '-v', '--validate',
        action='store_true',
        help='Validate output format'
    )
    
    args = parser.parse_args()
    
    print(f"Loading candidates from {args.input_file}...", file=sys.stderr)
    candidates = load_candidates(args.input_file)
    print(f"Loaded {len(candidates)} candidates", file=sys.stderr)
    
    # Initialize scorer
    print("Initializing scorer...", file=sys.stderr)
    scorer = CandidateScorer()
    
    # Rank candidates
    print("Ranking candidates...", file=sys.stderr)
    ranked_results = rank_candidates(candidates, scorer)
    
    # Validate if requested
    if args.validate:
        if not validate_output(ranked_results):
            sys.exit(1)
    
    # Write output
    print(f"Writing output to {args.output}...", file=sys.stderr)
    write_output(ranked_results, args.output)
    
    print("\nTop 10 candidates:", file=sys.stderr)
    for candidate_id, rank, score, reasoning in ranked_results[:10]:
        print(f"  {rank:3d}. {candidate_id}: {score:.4f} - {reasoning[:60]}", file=sys.stderr)
    
    print(f"\nRanking complete: {len(ranked_results)} candidates ranked to {args.output}", file=sys.stderr)


if __name__ == '__main__':
    main()
