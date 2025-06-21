#!/usr/bin/env python3
"""
Test script for the Elo rating system and value betting calculations.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.elo import elo_system, calculate_value_bet


def test_elo_ratings():
    """Test the Elo rating system."""
    print("🧪 Testing Elo Rating System")
    print("=" * 50)
    
    # Test team ratings
    print("\n📊 Current Team Ratings:")
    for team, rating in sorted(elo_system.ratings.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {team}: {rating}")
    
    # Test match probability calculations
    print("\n⚽ Match Probability Tests:")
    
    test_matches = [
        ("Manchester City", "Arsenal"),
        ("Liverpool", "Chelsea"),
        ("Newcastle United", "Burnley"),
        ("Brighton & Hove Albion", "Luton Town")
    ]
    
    for home, away in test_matches:
        probs = elo_system.calculate_match_probabilities(home, away)
        print(f"\n  {home} vs {away}:")
        print(f"    Home Win: {probs['home_win']:.1%}")
        print(f"    Draw:     {probs['draw']:.1%}")
        print(f"    Away Win: {probs['away_win']:.1%}")
        print(f"    Total:    {sum(probs.values()):.1%}")
    
    print("\n✅ Elo system tests completed!")


def test_value_betting():
    """Test value betting calculations."""
    print("\n🎯 Testing Value Betting Calculations")
    print("=" * 50)
    
    test_cases = [
        # (model_prob, bookmaker_odds, expected_result)
        (0.6, 2.0, "Value bet"),      # 60% chance, 2.0 odds (50% implied) = value
        (0.4, 2.0, "No value"),      # 40% chance, 2.0 odds (50% implied) = no value
        (0.7, 1.5, "Value bet"),     # 70% chance, 1.5 odds (66.7% implied) = small value
        (0.3, 4.0, "No value"),      # 30% chance, 4.0 odds (25% implied) = value but below threshold
    ]
    
    for model_prob, odds, expected in test_cases:
        value = calculate_value_bet(model_prob, odds)
        implied_prob = 1 / odds
        edge = model_prob - implied_prob
        
        print(f"\n  Model: {model_prob:.1%}, Odds: {odds}, Implied: {implied_prob:.1%}")
        print(f"  Edge: {edge:.1%}, Value: {value:.1f}%")
        print(f"  Result: {'✅' if value > 0 else '❌'} {expected}")
    
    print("\n✅ Value betting tests completed!")


def test_rating_updates():
    """Test rating updates after match results."""
    print("\n🔄 Testing Rating Updates")
    print("=" * 50)
    
    # Save original ratings
    original_city = elo_system.get_team_rating("Manchester City")
    original_arsenal = elo_system.get_team_rating("Arsenal")
    
    print(f"\n  Before match:")
    print(f"    Manchester City: {original_city}")
    print(f"    Arsenal: {original_arsenal}")
    
    # Simulate Arsenal beating Manchester City (upset)
    elo_system.update_ratings("Manchester City", "Arsenal", "away_win")
    
    new_city = elo_system.get_team_rating("Manchester City")
    new_arsenal = elo_system.get_team_rating("Arsenal")
    
    print(f"\n  After Arsenal beats Manchester City:")
    print(f"    Manchester City: {new_city} (change: {new_city - original_city:+.1f})")
    print(f"    Arsenal: {new_arsenal} (change: {new_arsenal - original_arsenal:+.1f})")
    
    # Restore original ratings
    elo_system.ratings["Manchester City"] = original_city
    elo_system.ratings["Arsenal"] = original_arsenal
    
    print("\n✅ Rating update tests completed!")


def main():
    """Run all tests."""
    print("🚀 Football Analytics Predictor - System Tests")
    print("=" * 60)
    
    try:
        test_elo_ratings()
        test_value_betting()
        test_rating_updates()
        
        print("\n🎉 All tests completed successfully!")
        print("\n📋 Next steps:")
        print("  1. Set up your ODDS_API_KEY in .env file")
        print("  2. Run: docker-compose up --build")
        print("  3. Visit http://localhost:3000 for the frontend")
        print("  4. Visit http://localhost:8000/docs for API documentation")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
