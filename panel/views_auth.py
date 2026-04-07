from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib import messages

def login_reseller(request):
    if request.method == "POST":
        u, p = request.POST.get('username'), request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user is not None:
            login(request, user)
            return redirect('reseller_panel')
        else:
            messages.error(request, "Usuario o contraseña incorrectos")
    return render(request, 'panel/login.html')

def logout_reseller(request):
    logout(request)
    return redirect('login_reseller')
