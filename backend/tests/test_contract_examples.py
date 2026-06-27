import unittest

from backend.app.models.examples import validate_examples


class ContractExampleTests(unittest.TestCase):
    def test_examples_match_model_contracts(self) -> None:
        validate_examples()


if __name__ == "__main__":
    unittest.main()

