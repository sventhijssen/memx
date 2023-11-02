import time
from math import floor

from networkx import weisfeiler_lehman_graph_hash, topological_generations, reverse

from utils import config
from core.decision_diagrams.BDDTopology import BDDTopology


class LOAD:

    def __init__(self, bdd_hash: str):
        self.bdd_hash = bdd_hash

    def __str__(self):
        return "LOAD {}".format(self.bdd_hash)

    def __repr__(self):
        return "LOAD {}".format(self.bdd_hash)

    def to_json(self):
        return {
            "type": "LOAD",
            "hash": self.bdd_hash
        }


class EVAL:

    def __init__(self, bdd_hash: str):
        self.bdd_hash = bdd_hash

    def __str__(self):
        return "EVAL {}".format(self.bdd_hash)

    def __repr__(self):
        return "EVAL {}".format(self.bdd_hash)

    def to_json(self):
        return {
            "type": "EVAL",
            "hash": self.bdd_hash
        }


class ISO:

    def __init__(self, bdd_topology: BDDTopology, D: int):
        """
        This synthesis method is based on the ISO framework in [1].

        [1] Thijssen, S., Rashed, M., Zheng, H., Jha, S. K., & Ewetz, R. (2024, January).
        Towards Area-Efficient Path-Based In-Memory Computing using Graph Isomorphisms.
        In 2024 29th Asia and South Pacific Design Automation Conference (ASP-DAC). IEEE. (accepted)

        """

        # TODO: We must define a new structure in the future that holds both the crossbar designs and the instructions.

        self.bdd_topology = bdd_topology
        self.D = D
        self.start_time = None
        self.end_time = None

    def find(self):
        self.start_time = time.time()
        root_node_to_hash = dict()
        bdd_patterns = dict()
        for root_node, bdd in self.bdd_topology.bdds.items():
            bdd_hash = weisfeiler_lehman_graph_hash(bdd.dag, digest_size=16)
            root_node_to_hash[root_node] = bdd_hash
            if bdd_hash not in bdd_patterns:
                bdd_patterns[bdd_hash] = set()
            bdd_patterns[bdd_hash].add(bdd)

        generations = list(topological_generations(reverse(self.bdd_topology.topology)))

        # We remove the primary input variables
        new_generations = []
        for generation in generations:
            new_generation = []
            for node in generation:
                if node in self.bdd_topology.bdds.keys():
                    new_generation.append(node)
            new_generations.append(new_generation)
        generations = new_generations

        # for hash, bdds in bdd_patterns.items():
        #     bdd = list(bdds)[0]
        #     content = list(bdd.draw())[0]
        #     with open("{}.dot".format(bdd.name), 'w') as f:
        #         f.write(content)
        #     print(hash)
        #     for bdd in bdds:
        #         print("\t{}".format(bdd.get_output_variables()))

        json_content = dict()
        json_content["patterns"] = []
        bdd_pattern_stats = dict()
        for bdd_hash, bdds in bdd_patterns.items():
            bdd = list(bdds)[0]
            json_content["patterns"].append({
                "hash": bdd_hash,
                "nr_bdds": len(bdds),
                "nodes": len(bdd.dag.nodes),
                "edges": len(bdd.dag.edges)
            })
            bdd_pattern_stats[bdd_hash] = [
                len(bdds),
                len(bdd.dag.nodes),
                len(bdd.dag.edges)
            ]

        total_rows = 0
        total_cols = 0
        total_semi = 0
        for bdds in bdd_patterns.values():
            bdd = list(bdds)[0]
            rows = len(bdd.dag.nodes)
            cols = len(bdd.dag.edges)
            total_rows += rows * len(bdds)
            total_cols += cols * len(bdds)
            total_semi += (rows + cols) * len(bdds)
        total_area = total_rows * total_cols
        cycles = len(generations)
        self.end_time = time.time()
        print("Before optimization:")
        print("Rows: {}".format(total_rows))
        print("Cols: {}".format(total_cols))
        print("Semi: {}".format(total_semi))
        print("Area: {}".format(total_area))

        json_content["before"] = {
            "rows": total_rows,
            "cols": total_cols,
            "semi": total_semi,
            "area": total_area,
            "cycles": cycles,
            "total_time": self.end_time - self.start_time
        }

        self.start_time = time.time()
        new_generations = []
        while len(generations) != 0:
            root_node_generation = generations.pop(0)
            hash_generation = list(filter(lambda y: y is not None, map(lambda x: root_node_to_hash.get(x), list(root_node_generation))))
            hash_to_nodes = dict()
            for i in range(len(hash_generation)):
                bdd_hash = hash_generation[i]
                root_node = root_node_generation[i]
                if bdd_hash not in hash_to_nodes:
                    hash_to_nodes[bdd_hash] = []
                hash_to_nodes[bdd_hash].append(root_node)

            # We keep the first one and push down the other ones to a new generation
            # We cannot add the other ones to the next generation, since they depend on the next generation
            # From the description of NetworkX's implementation for topological_generations:
            # "Nodes are guaranteed to be in the earliest possible generation that they can belong to."
            # Thus, by contradiction, a new layer must be created.
            kept_nodes = []
            pushed_down_nodes = []
            for bdd_hash, root_nodes in hash_to_nodes.items():
                kept_nodes.append(root_nodes[0])
                if len(root_nodes) > 1:
                    pushed_down_nodes.extend(root_nodes[1:])
            new_generations.append(kept_nodes)
            if len(pushed_down_nodes) > 0:
                generations.insert(0, pushed_down_nodes)
        generations = new_generations  # Ordered from output -> input. For evaluation, the reverse is needed.

        # for generation in new_generations:
        #     print(list(map(lambda x: root_node_to_hash.get(x), generation)))

        total_rows = 0
        total_cols = 0
        total_semi = 0
        for bdds in bdd_patterns.values():
            bdd = list(bdds)[0]
            rows = len(bdd.dag.nodes)
            cols = len(bdd.dag.edges)
            total_rows += rows
            total_cols += cols
            total_semi += (rows + cols)
        total_area = total_rows * total_cols
        cycles = len(generations)
        self.end_time = time.time()
        print("After optimization:")
        print("Rows: {}".format(total_rows))
        print("Cols: {}".format(total_cols))
        print("Semi: {}".format(total_semi))
        print("Area: {}".format(total_area))

        json_content["after"] = {
            "rows": total_rows,
            "cols": total_cols,
            "semi": total_semi,
            "area": total_area,
            "cycles": cycles,
            "total_time": self.end_time - self.start_time
        }

        config.log.add_json(json_content)

        if self.D is not None:
            json_content = dict()
            self.start_time = time.time()

            sorted_bdd_pattern_stats = dict(sorted(bdd_pattern_stats.items(), key=lambda item: item[1], reverse=True))
            sorted_bdd_pattern_keys = list(sorted_bdd_pattern_stats.keys())
            sorted_bdd_pattern_values = list(sorted_bdd_pattern_stats.values())

            low = 0
            high = len(sorted_bdd_pattern_stats)
            mid = floor((low + high) / 2)
            while low <= high:
                fixed_rows = sum(list(map(lambda x: x[1], sorted_bdd_pattern_values[:mid])))
                fixed_columns = sum(list(map(lambda x: x[2], sorted_bdd_pattern_values[:mid])))
                if fixed_rows > self.D or fixed_columns > self.D:
                    high = mid - 1
                    mid = floor((low + high) / 2)
                else:
                    if mid == len(sorted_bdd_pattern_values):
                        largest_variable_row = 0
                        largest_variable_column = 0
                    else:
                        largest_variable_row = max(list(map(lambda x: x[1], sorted_bdd_pattern_values[mid:])))
                        largest_variable_column = max(list(map(lambda x: x[2], sorted_bdd_pattern_values[mid:])))
                    if fixed_rows + largest_variable_row > self.D or fixed_columns + largest_variable_column > self.D:
                        high = mid - 1
                        mid = floor((low + high) / 2)
                    else:
                        low = mid + 1
                        mid = floor((low + high) / 2)

            fixed_rows = sum(list(map(lambda x: x[1], sorted_bdd_pattern_values[:mid])))
            fixed_columns = sum(list(map(lambda x: x[2], sorted_bdd_pattern_values[:mid])))
            if mid == len(sorted_bdd_pattern_values):
                largest_variable_row = 0
                largest_variable_column = 0
            else:
                largest_variable_row = max(list(map(lambda x: x[1], sorted_bdd_pattern_values[mid:])))
                largest_variable_column = max(list(map(lambda x: x[2], sorted_bdd_pattern_values[mid:])))
            print("Mid: {}".format(mid))
            print("Max rows: {}".format(fixed_rows + largest_variable_row))
            print("Max cols: {}".format(fixed_columns + largest_variable_column))

            if fixed_rows + largest_variable_row > self.D or fixed_columns + largest_variable_column > self.D:
                raise Exception("Binary search failed.")

            # Now that we have determined the BDDs which are fixed, we will start the scheduling for program execution
            reversed_generations = list(reversed(generations))[1:]

            cycles = []
            cycle = []
            # These are the fixed BDDs
            fixed_bdds = set()
            variable_bdd = None
            for i in range(mid):
                cycle.append(LOAD(sorted_bdd_pattern_keys[i]))
                fixed_bdds.add(sorted_bdd_pattern_keys[i])

            if len(cycle) > 0:
                cycles.append(cycle)

            for i in range(len(reversed_generations)):
                generation = set(reversed_generations[i])
                all_bdds = set(map(lambda r: root_node_to_hash.get(r), generation))

                evaluated_bdds = set()
                for root_node in generation:
                    bdd_hash = root_node_to_hash.get(root_node)
                    if bdd_hash in fixed_bdds:
                        evaluated_bdds.add(bdd_hash)
                    if bdd_hash == variable_bdd:
                        evaluated_bdds.add(bdd_hash)

                cycle = []
                for evaluated_bdd in evaluated_bdds:
                    cycle.append(EVAL(evaluated_bdd))
                if len(cycle) > 0:
                    cycles.append(cycle)

                missed_bdds = all_bdds - evaluated_bdds  # Determines the number of cycles remaining

                for missed_bdd in missed_bdds:
                    variable_bdd = missed_bdd
                    cycle = [LOAD(missed_bdd)]
                    cycles.append(cycle)
                    cycle = [EVAL(missed_bdd)]
                    cycles.append(cycle)

            self.end_time = time.time()
            print("Number of cycles: {}".format(len(cycles)))

            json_content["cycles"] = {
                "cycles": [list(map(lambda instruction: instruction.to_json(), cycle)) for cycle in cycles],
                "total_time": self.end_time - self.start_time
            }

            config.log.add_json(json_content)

        print("End")
