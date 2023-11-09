import sys

from crossword import *


class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        _, _, w, h = draw.textbbox((0, 0), letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        for var in self.domains:
            consistent_values = [
                value for value in self.domains[var] if len(value) == var.length
            ]
            self.domains[var] = consistent_values

    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        revised = False  # Flag to track if a revision was made

        overlap = self.crossword.overlaps[x, y]  # Get the overlap between variables x and y

        if overlap is None:
            return revised  # If no overlap, no revision can be made

        overlap_x, overlap_y = overlap
        x_domain = self.domains[x]
        y_domain = self.domains[y]

        # Iterate over each value in the domain of x
        for val_x in x_domain.copy():
            # check wheater there is any world in y's domain that has a letter that overlaps with val_x
            has_corresponding_value = any(
                val_x[overlap_x] == val_y[overlap_y]
                for val_y in y_domain
            )
        
            if not has_corresponding_value:
                x_domain.remove(val_x)  # Remove value from x's domain
                revised = True
    
        return revised


    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        queue = arcs if arcs is not None else list(self.crossword.overlaps)

        while queue:
            x,y = queue.pop()
            if self.revise(x,y):
                if not self.domains[x]:
                    return False
                
                # Add additional arcs to the queue for variables affected by the revision
                for z in self.crossword.neighbors(x) - {y}:
                    queue.append((z, x))

        return True

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        return all(variable in assignment for variable in self.domains.keys())

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        # Check for correct values and correct lengths
        assigned_values = set()

        for var in assignment:
            if var.length != len(assignment[var]) or assignment[var] in assigned_values:
                return False
            assigned_values.add(assignment[var])

        # Check for conflicts between neighboring variables
        for var1, var2 in self.crossword.overlaps.keys():
            if (var1 in assignment) and (var2 in assignment):
                overlap_positions = self.crossword.overlaps[(var1, var2)]
                if overlap_positions is not None:
                    overlap_x, overlap_y = overlap_positions
                    if assignment[var1][overlap_x] != assignment[var2][overlap_y]:
                        return False
        
        return True

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        def count_eliminated_values(value, variable):
            eliminated = 0
            for neighbor in self.crossword.neighbors(variable) - assignment.keys():
                overlap = self.crossword.overlaps[var, neighbor]
                if overlap:
                    index_var, index_neighbor = overlap
                    eliminated += sum(1 for val in self.domains[neighbor]
                                    if val[index_neighbor] != value[index_var])
            return eliminated
    
        domain = list(self.domains[var])  # Get the domain of the variable
        domain.sort(key=lambda value: count_eliminated_values(value, var))
        return domain

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        unassigned_variables = [
            var for var in self.domains if var not in assignment
        ]

        def key_function(variable):
            return (len(self.domains[variable]), -len(self.crossword.neighbors(variable)))

        unassigned_variables.sort(key=key_function)
        return unassigned_variables[0]

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
        if self.assignment_complete(assignment):
            return assignment
        
        var = self.select_unassigned_variable(assignment)
        for value in self.order_domain_values(var, assignment):
            new_assignment = assignment.copy()
            new_assignment[var] = value

            if self.consistent(new_assignment):
                result = self.backtrack(new_assignment)
                if result is not None:
                    return result
        return None
        """
        if self.assignment_complete(assignment):
            return assignment
        
        var = self.select_unassigned_variable(assignment)

        for value in self.order_domain_values(var, assignment):
            new_assignment = assignment.copy()
            new_assignment[var] = value

            if self.consistent(new_assignment):
                assignment[var] = value

                # Apply AC-3
                if not self.ac3([(neighbor, var) for neighbor in self.crossword.neighbors(var)]):
                    del assignment[var]  # Backtrack if inconsistency found
                    continue
            
                result = self.backtrack(assignment) # Recurse
                if result is not None:
                    return result # Solution found
                
                del assignment[var] # Backtrack
        return None # No solution found
        """


def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
