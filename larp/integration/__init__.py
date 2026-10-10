"""Cross-component adapters (IDEA-028 RT21). Owner: Keegan.

They connect the runtime coordinator to the strategy/risk modules, the execution
machine and the accounting reducer through the shared ports. They hold no
credentials and add no external I/O of their own; every data source is injected.
"""
