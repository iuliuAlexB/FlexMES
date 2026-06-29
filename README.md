FlexMES V2 — Ghid de Instalare și Rulare

Aceste programe trebuie sa existe preinstalate:

GIT
Git	https://git-scm.com/download/win
verificati in cmd cu git --version

DOCKER
Docker Desktop	https://www.docker.com/products/docker-desktop
verificati in cmd cu 	docker --version

INSTALARE SI PORNIRE

PASUL 0 — Pornește Docker Desktop
Așteaptă până iconița din system tray nu mai are loading.

PASUL 1 — Descărcare cod sursă
Rulează în terminal (CMD sau PowerShell):
git clone https://github.com/iuliuAlexB/FlexMES.git
cd FlexMES

PASUL 2 — Build și pornire
Prima rulare durează aproximativ 3 minute:
docker compose up --build
Aplicația este gată când apare în terminal:
INFO: Application startup complete

PASUL 3 — Accesare
Deschide browserul:
http://localhost:8000
Credențiale demo

admin	admin123	Manager — acces complet
operator1	op123	Operator — Panou QC S4

OPRIRE
docker compose down

