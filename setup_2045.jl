using PyCall

cd("/Volumes/GoogleDrive/My Drive/Consulting_Projects/CATF WRA Arizona/AZ_Modeling/AZ-22x5/")

# I don't think this is necessary, but try using if the script doesn't work.
pushfirst!(PyVector(pyimport("sys")."path"), "")

@pyimport importlib.machinery as machinery
loader = machinery.SourceFileLoader("setup_2045_cases","setup_2045_cases.py")
my_mod = loader[:load_module]("setup_2045_cases")
my_mod.transfer_2030_results()
