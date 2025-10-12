#!/bin/bash
# Run unit tests for SlickNXT execution engine

echo "Running SlickNXT Execution Engine Tests..."
echo "=========================================="
python -m pytest tests/test_execution_engine.py -v --tb=short

echo ""
echo "To run specific tests:"
echo "  pytest tests/test_execution_engine.py::TestDialNode -v"
echo ""
echo "To run with coverage:"
echo "  pytest tests/ --cov=app/execution_engine --cov-report=html"

