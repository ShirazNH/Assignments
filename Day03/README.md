## Assignment 3

For this assignment, I opened a new folder and named it *Day03*. I added a Data folder with data from my experiments on mating abilities of a clock-gene mutant. I asked Claude to write a program that calculates a *mating efficiency index*.

The prompt I used:
> Hi Claude, For my Day03 assignment, please write a python program that calculates a mating efficiency index for each male in @Day03/Data/mating_efficiency_data.xlsx . The index is the fraction of hermaphrodites (herm_1-4) that have progeny (have a score 1) out of the 4 hermaphrodites that were tested with that male. Please add a column with the index of each male, and calculate he average index of each group according to the 'Genotype' column'. Don't make changes directly to the @Day03/Data/mating_efficiency_data.xlsx , create a new file for that.

After that I have noticed I have the temporary files on GitHub, so I asked Claude why do I see them there, then I deleted them and asked Claude to write me a .gitignore file.

> Am I supposed to see all of these in my repo?

> Just create the gitignore file, I will delete the files and then commit and push myself