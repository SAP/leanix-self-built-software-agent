import json
from typing import Set

from src.dto.gold_standard_dto import GoldExpectedOutput
from src.dto.state_dto import RootRepoState
from src.logging.logging import get_logger

logger = get_logger(__name__)

def simple_evaluation(output, expected_output) -> bool:
    return output == expected_output

def names_from_state(state: RootRepoState) -> Set[str]:
    return {
        c.name.strip().lower()
        for c in state.self_built_software or []
        if isinstance(c.name, str) and c.name.strip()
    }

def names_from_gold(gold: GoldExpectedOutput) -> Set[str]:
    return {
        comp["name"].strip().lower()
        for comp in gold["self_built_software"]
        if isinstance(comp.get("name"), str) and comp["name"].strip()
    }


def sbs_name_evaluation(pred: RootRepoState, gold: GoldExpectedOutput) -> float:
    """
    Calculate accuracy score considering both missing items and false positives.

    Score = (true_positives / total_expected) - (false_positives / total_expected)

    Examples:
    - Expected: {A, B, C}, Predicted: {A, C} → Score = 2/3 ≈ 0.67
    - Expected: {A, B, C}, Predicted: {D, E} → Score = 0/3 = 0.0
    - Expected: {A, B, C}, Predicted: {A, B, C, D} → Score = 3/3 - 1/3 ≈ 0.67
    """
    gold_names = names_from_gold(gold)
    if not gold_names:
        return 1.0 if not pred.self_built_software else 0.0

    pred_names = names_from_state(pred)

    true_positives = len(pred_names & gold_names)  # Correctly identified
    false_positives = len(pred_names - gold_names)  # Incorrectly identified
    total_expected = len(gold_names)

    score = (true_positives / total_expected) - (false_positives / total_expected)

    # Ensure score doesn't go below 0
    return max(0.0, score)


def calculate_recall(pred: RootRepoState, gold: GoldExpectedOutput) -> float:
    """Recall = true_positives / total_expected"""
    gold_names = names_from_gold(gold)
    if not gold_names:
        return 1.0

    pred_names = names_from_state(pred)
    true_positives = len(pred_names & gold_names)
    return true_positives / len(gold_names)

def normalize_teams(team):
    if isinstance(team, str):
        return {t.strip().lower() for t in team.split(";") if t.strip()}
    elif isinstance(team, list):
        return {t.strip().lower() for t in team if isinstance(t, str) and t.strip()}
    return set()

def team_name_evaluation(pred: RootRepoState, gold: GoldExpectedOutput) -> float:
    if pred.deployable:
        logger.info(f"Evaluating team names for repo: {getattr(pred, 'repo_root_url', None)}")
        pred_components = {c.name.strip().lower(): normalize_teams(getattr(c.owner, "team", "")) for c in pred.self_built_software or []}
        gold_components = {comp["name"].strip().lower(): normalize_teams(comp.get("owner", {}).get("team", "")) for comp in gold["self_built_software"]}

        if not gold_components:
            logger.info("No gold teams found, returning 0.0")
            return 0.0

        matches = 0
        total = len(gold_components)
        for name, gold_teams in gold_components.items():
            pred_teams = pred_components.get(name, set())
            logger.info(f"Gold component: {name}, teams: {gold_teams}")
            logger.info(f"Predicted component: {name}, teams: {pred_teams}")

            found = False
            for gold_team in gold_teams:
                if gold_team.lower() == "na":
                    if not pred_teams or any(not pt or pt.strip() == "" for pt in pred_teams):
                        found = True
                        break
                elif any(gold_team == pt for pt in pred_teams):
                    found = True
                    break
            if found:
                matches += 1
                logger.info(f"Match found for component: {name}")

        score = matches / total if total > 0 else 0.0
        logger.info(f"{matches} matches out of {total}, score: {score}")
        return score
    else:
        logger.info("Skipping team name evaluation for non-deployable repo")
        return 1.0

def team_name_evaluation_boolean(pred: RootRepoState, gold: GoldExpectedOutput) -> float:
    score = team_name_evaluation(pred, gold)
    if score == 1.0:
        return True
    else:
        return False

def sbs_language_evaluation(pred, gold):
    try:
        if not pred.self_built_software:
            logger.info("No predicted self_built_software; returning True.")
            return True

        logger.info(f"Evaluating language for pred: {pred.self_built_software}")

        pred_languages = set()
        for c in pred.self_built_software:
            lang = getattr(c, "language", None)
            if isinstance(lang, str):
                try:
                    lang = json.loads(lang)
                except Exception as e:
                    logger.warning(f"Failed to parse language JSON: {lang} ({e})")
                    continue
            if lang and isinstance(lang, dict):
                name = lang.get("name")
                version = lang.get("version")
                if name and version:
                    pred_languages.add((name, version))
        logger.info(f"Predicted languages: {pred_languages}")

        gold_languages = set()
        for comp in gold.get("self_built_software", []):
            lang = comp.get("language", {})
            name = lang.get("name")
            version = lang.get("version")
            if name and version:
                gold_languages.add((name, version))
        logger.info(f"Gold languages: {gold_languages}")

        result = pred_languages == gold_languages
        logger.info(f"Language evaluation result: {result}")
        return result
    except Exception as e:
        logger.error(f"Exception during language evaluation: {e}")
        return False

def individual_contributors_evaluation_boolean(pred: RootRepoState) -> bool:
    """Evaluate if all self-built software components have at least one individual contributor."""

    evaluation : bool = True

    if pred.deployable:
        logger.info(f"Evaluating individual contributors for repo: {getattr(pred, 'repo_root_url', None)}")
        evaluation = all(len(sbs.owner.individuals) > 0 for sbs in pred.self_built_software)

    return evaluation

def sbs_count_and_names_match(pred: RootRepoState, gold: GoldExpectedOutput) -> bool:
    pred_names = [c.name.strip().lower() for c in pred.self_built_software or [] if isinstance(c.name, str) and c.name.strip()]
    gold_names = [comp["name"].strip().lower() for comp in gold["self_built_software"] if isinstance(comp.get("name"), str) and comp["name"].strip()]
    return len(pred_names) == len(gold_names) and all(name in gold_names for name in pred_names)

def tech_stack_name_evaluation_boolean(pred: RootRepoState, gold: GoldExpectedOutput) -> bool:
    pred_components = {c.name: c for c in pred.self_built_software}
    gold_components = gold["self_built_software"]

    for gold_comp in gold_components:
        gold_name = gold_comp["name"]
        if gold_name not in pred_components:
            logger.info(f"Component '{gold_name}' not found in prediction, skipping.")
            continue

        pred_comp = pred_components[gold_name]
        pred_tech_names = {ts.name.lower() for ts in getattr(pred_comp, "tech_stacks", [])}
        gold_tech_names = {ts["name"].lower() for ts in gold_comp.get("tech_stacks", [])}

        missing = gold_tech_names - pred_tech_names
        if missing:
            logger.info(f"Missing tech stack name in component '{gold_name}'. Missing tech stacks: {missing}")
            return False
        else:
            logger.info(f"Component '{gold_name}' all tech stacks (names) present.")

    return True


def tech_stack_name_and_version_evaluation_boolean(pred: RootRepoState, gold: GoldExpectedOutput) -> bool:
    pred_components = {c.name: c for c in pred.self_built_software}
    gold_components = gold["self_built_software"]

    for gold_comp in gold_components:
        gold_name = gold_comp["name"]
        if gold_name not in pred_components:
            logger.info(f"Component '{gold_name}' not found in prediction, skipping.")
            continue

        pred_comp = pred_components[gold_name]
        pred_tech = {(ts.name.lower(), ts.version) for ts in getattr(pred_comp, "tech_stacks", [])}
        gold_tech = {(ts["name"].lower(), ts.get("version")) for ts in gold_comp.get("tech_stacks", [])}

        missing = gold_tech - pred_tech
        if missing:
            logger.info(f"Missing tech stack name/version in component '{gold_name}'. Missing tech stacks: {missing}")
            return False
        else:
            logger.info(f"Component '{gold_name}' all tech stacks (names and versions) present.")

    return True
