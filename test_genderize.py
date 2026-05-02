from app.services. import predict_genders
results = predict_genders(["Hijo de Sandra", "Hija de Maria", "Erick"])
for r in results:
    print(r.name, "->", r.gender)