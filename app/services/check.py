import os
for f in sorted(os.listdir("app/services")):
    if "genderize" in f:
        print(repr(f), len(open("app/services/" + f).read()))