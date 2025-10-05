import unittest
from event_planner_agent.agent import root_agent

class TestAgentCreation(unittest.TestCase):
    def test_root_agent_creation(self):
        self.assertIsNotNone(root_agent)
        self.assertEqual(root_agent.name, "event_planner_agent")

if __name__ == '__main__':
    unittest.main()