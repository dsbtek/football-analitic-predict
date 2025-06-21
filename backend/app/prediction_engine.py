"""
Enhanced prediction engine for match outcome predictions and custom odds requests.
"""

import random
import math
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from app.elo import elo_system
import logging

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    """Result of a match prediction."""
    home_team: str
    away_team: str
    predicted_outcome: str  # 'home', 'draw', 'away'
    confidence: float  # 0-100
    probabilities: Dict[str, float]
    reasoning: str
    risk_level: str  # 'low', 'medium', 'high'
    expected_value: float


@dataclass
class OddsRequest:
    """User request for specific odds combinations."""
    target_odds: float
    max_matches: int
    risk_tolerance: str  # 'conservative', 'moderate', 'aggressive'
    preferred_outcomes: List[str]  # ['home', 'draw', 'away']


class EnhancedPredictionEngine:
    """Enhanced prediction engine with AI-powered insights."""
    
    def __init__(self):
        self.elo_system = elo_system
        self.confidence_threshold = 0.65  # Minimum confidence for recommendations
        
    def predict_match_outcome(self, home_team: str, away_team: str, 
                            additional_factors: Optional[Dict] = None) -> PredictionResult:
        """
        Predict match outcome with enhanced analysis.
        
        Args:
            home_team: Name of home team
            away_team: Name of away team
            additional_factors: Optional factors like injuries, form, etc.
            
        Returns:
            Detailed prediction result
        """
        # Get base probabilities from Elo system
        base_probs = self.elo_system.calculate_match_probabilities(home_team, away_team)
        
        # Apply additional factors
        adjusted_probs = self._apply_additional_factors(base_probs, additional_factors)
        
        # Determine predicted outcome
        predicted_outcome = max(adjusted_probs, key=adjusted_probs.get)
        outcome_map = {'home_win': 'home', 'draw': 'draw', 'away_win': 'away'}
        predicted_outcome = outcome_map[predicted_outcome]
        
        # Calculate confidence
        confidence = self._calculate_confidence(adjusted_probs)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(home_team, away_team, adjusted_probs, additional_factors)
        
        # Determine risk level
        risk_level = self._determine_risk_level(confidence, adjusted_probs)
        
        # Calculate expected value (simplified)
        expected_value = self._calculate_expected_value(adjusted_probs)
        
        return PredictionResult(
            home_team=home_team,
            away_team=away_team,
            predicted_outcome=predicted_outcome,
            confidence=round(confidence * 100, 1),
            probabilities={
                'home': round(adjusted_probs['home_win'] * 100, 1),
                'draw': round(adjusted_probs['draw'] * 100, 1),
                'away': round(adjusted_probs['away_win'] * 100, 1)
            },
            reasoning=reasoning,
            risk_level=risk_level,
            expected_value=round(expected_value, 2)
        )
    
    def find_matches_for_odds(self, request: OddsRequest, available_matches: List[Dict]) -> List[Dict]:
        """
        Find match combinations that meet user's odds requirements.
        
        Args:
            request: User's odds request
            available_matches: List of available matches
            
        Returns:
            List of match combinations with their combined odds
        """
        combinations = []
        
        # Single match combinations
        for match in available_matches:
            for outcome in ['home', 'draw', 'away']:
                odds_key = f"{outcome}_odds"
                if odds_key in match and match[odds_key]:
                    odds = match[odds_key]
                    
                    # Check if odds match criteria
                    if self._odds_meets_criteria(odds, request.target_odds, request.risk_tolerance):
                        prediction = self.predict_match_outcome(match['home'], match['away'])
                        
                        combination = {
                            'type': 'single',
                            'matches': [match],
                            'outcomes': [outcome],
                            'combined_odds': odds,
                            'prediction_confidence': prediction.confidence,
                            'risk_level': prediction.risk_level,
                            'description': f"{match['home']} vs {match['away']} - {outcome.title()} Win",
                            'reasoning': prediction.reasoning
                        }
                        combinations.append(combination)
        
        # Double match combinations (accumulators)
        if request.max_matches >= 2:
            combinations.extend(self._generate_double_combinations(available_matches, request))
        
        # Triple match combinations
        if request.max_matches >= 3:
            combinations.extend(self._generate_triple_combinations(available_matches, request))
        
        # Sort by relevance to target odds and confidence
        combinations.sort(key=lambda x: (
            abs(x['combined_odds'] - request.target_odds),
            -x['prediction_confidence']
        ))
        
        return combinations[:10]  # Return top 10 combinations
    
    def _apply_additional_factors(self, base_probs: Dict[str, float], 
                                factors: Optional[Dict] = None) -> Dict[str, float]:
        """Apply additional factors to base probabilities."""
        if not factors:
            return base_probs
        
        adjusted = base_probs.copy()
        
        # Example factors (in a real system, these would be more sophisticated)
        if 'home_form' in factors:
            form_factor = factors['home_form'] / 10  # Assuming 1-10 scale
            adjusted['home_win'] *= (1 + form_factor * 0.1)
        
        if 'away_form' in factors:
            form_factor = factors['away_form'] / 10
            adjusted['away_win'] *= (1 + form_factor * 0.1)
        
        if 'injuries' in factors:
            injury_impact = factors['injuries'] / 10  # Negative impact
            adjusted['home_win'] *= (1 - injury_impact * 0.05)
            adjusted['away_win'] *= (1 - injury_impact * 0.05)
            adjusted['draw'] *= (1 + injury_impact * 0.1)
        
        # Normalize probabilities
        total = sum(adjusted.values())
        return {k: v / total for k, v in adjusted.items()}
    
    def _calculate_confidence(self, probabilities: Dict[str, float]) -> float:
        """Calculate prediction confidence based on probability distribution."""
        max_prob = max(probabilities.values())
        prob_spread = max_prob - min(probabilities.values())
        
        # Higher confidence when there's a clear favorite
        confidence = max_prob + (prob_spread * 0.5)
        return min(confidence, 1.0)
    
    def _generate_reasoning(self, home_team: str, away_team: str, 
                          probabilities: Dict[str, float], factors: Optional[Dict] = None) -> str:
        """Generate human-readable reasoning for the prediction."""
        home_rating = self.elo_system.get_team_rating(home_team)
        away_rating = self.elo_system.get_team_rating(away_team)
        
        rating_diff = home_rating - away_rating
        
        reasoning_parts = []
        
        # Rating analysis
        if rating_diff > 100:
            reasoning_parts.append(f"{home_team} has a significant rating advantage ({home_rating:.0f} vs {away_rating:.0f})")
        elif rating_diff > 50:
            reasoning_parts.append(f"{home_team} has a moderate rating advantage")
        elif rating_diff < -100:
            reasoning_parts.append(f"{away_team} has a significant rating advantage ({away_rating:.0f} vs {home_rating:.0f})")
        elif rating_diff < -50:
            reasoning_parts.append(f"{away_team} has a moderate rating advantage")
        else:
            reasoning_parts.append("Teams are closely matched in terms of rating")
        
        # Home advantage
        reasoning_parts.append("Home advantage provides additional edge")
        
        # Probability analysis
        max_outcome = max(probabilities, key=probabilities.get)
        max_prob = probabilities[max_outcome] * 100
        
        if max_prob > 60:
            reasoning_parts.append(f"Strong likelihood of {max_outcome.replace('_', ' ')} ({max_prob:.1f}%)")
        elif max_prob > 45:
            reasoning_parts.append(f"Moderate likelihood of {max_outcome.replace('_', ' ')} ({max_prob:.1f}%)")
        else:
            reasoning_parts.append("Match outcome is highly uncertain")
        
        return ". ".join(reasoning_parts) + "."
    
    def _determine_risk_level(self, confidence: float, probabilities: Dict[str, float]) -> str:
        """Determine risk level based on confidence and probability spread."""
        max_prob = max(probabilities.values())
        
        if confidence > 0.8 and max_prob > 0.6:
            return 'low'
        elif confidence > 0.6 and max_prob > 0.45:
            return 'medium'
        else:
            return 'high'
    
    def _calculate_expected_value(self, probabilities: Dict[str, float]) -> float:
        """Calculate expected value of the prediction."""
        # Simplified EV calculation
        max_prob = max(probabilities.values())
        return (max_prob - 0.33) * 100  # Compared to random chance
    
    def _odds_meets_criteria(self, odds: float, target_odds: float, risk_tolerance: str) -> bool:
        """Check if odds meet user criteria."""
        tolerance_ranges = {
            'conservative': 0.2,  # ±0.2
            'moderate': 0.5,      # ±0.5
            'aggressive': 1.0     # ±1.0
        }
        
        tolerance = tolerance_ranges.get(risk_tolerance, 0.5)
        return abs(odds - target_odds) <= tolerance
    
    def _generate_double_combinations(self, matches: List[Dict], request: OddsRequest) -> List[Dict]:
        """Generate double match combinations."""
        combinations = []
        
        for i, match1 in enumerate(matches):
            for j, match2 in enumerate(matches[i+1:], i+1):
                for outcome1 in request.preferred_outcomes or ['home', 'draw', 'away']:
                    for outcome2 in request.preferred_outcomes or ['home', 'draw', 'away']:
                        odds1 = match1.get(f"{outcome1}_odds", 0)
                        odds2 = match2.get(f"{outcome2}_odds", 0)
                        
                        if odds1 and odds2:
                            combined_odds = odds1 * odds2
                            
                            if self._odds_meets_criteria(combined_odds, request.target_odds, request.risk_tolerance):
                                pred1 = self.predict_match_outcome(match1['home'], match1['away'])
                                pred2 = self.predict_match_outcome(match2['home'], match2['away'])
                                
                                avg_confidence = (pred1.confidence + pred2.confidence) / 2
                                
                                combination = {
                                    'type': 'double',
                                    'matches': [match1, match2],
                                    'outcomes': [outcome1, outcome2],
                                    'combined_odds': round(combined_odds, 2),
                                    'prediction_confidence': round(avg_confidence, 1),
                                    'risk_level': 'high' if avg_confidence < 60 else 'medium',
                                    'description': f"Double: {match1['home']} vs {match1['away']} ({outcome1}) + {match2['home']} vs {match2['away']} ({outcome2})",
                                    'reasoning': f"Combined prediction with {avg_confidence:.1f}% confidence"
                                }
                                combinations.append(combination)
        
        return combinations
    
    def _generate_triple_combinations(self, matches: List[Dict], request: OddsRequest) -> List[Dict]:
        """Generate triple match combinations (simplified for performance)."""
        combinations = []
        
        # Limit to first 5 matches for performance
        limited_matches = matches[:5]
        
        for i, match1 in enumerate(limited_matches):
            for j, match2 in enumerate(limited_matches[i+1:], i+1):
                for k, match3 in enumerate(limited_matches[j+1:], j+1):
                    # Only try most likely outcomes to limit combinations
                    for outcome in ['home', 'away']:  # Skip draw for triples
                        odds1 = match1.get(f"{outcome}_odds", 0)
                        odds2 = match2.get(f"{outcome}_odds", 0)
                        odds3 = match3.get(f"{outcome}_odds", 0)
                        
                        if odds1 and odds2 and odds3:
                            combined_odds = odds1 * odds2 * odds3
                            
                            if self._odds_meets_criteria(combined_odds, request.target_odds, request.risk_tolerance):
                                combination = {
                                    'type': 'triple',
                                    'matches': [match1, match2, match3],
                                    'outcomes': [outcome, outcome, outcome],
                                    'combined_odds': round(combined_odds, 2),
                                    'prediction_confidence': 30,  # Lower confidence for triples
                                    'risk_level': 'high',
                                    'description': f"Triple {outcome}: {match1['home']} vs {match1['away']}, {match2['home']} vs {match2['away']}, {match3['home']} vs {match3['away']}",
                                    'reasoning': "High-risk triple combination"
                                }
                                combinations.append(combination)
        
        return combinations


# Global prediction engine instance
prediction_engine = EnhancedPredictionEngine()
