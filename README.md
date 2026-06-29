FlexMES V2 — Ghid de Instalare și Rulare

Cerințe preliminare
Aceste programe trebuie sa existe preinstalate:

Software	Link download	Verificare
Git	https://git-scm.com/download/win	git --version
Docker Desktop	https://www.docker.com/products/docker-desktop	docker --version
Browser modern	Chrome / Firefox / Edge	—
Instalare și pornire
Pasul 0 — Pornește Docker Desktop
Așteaptă până iconița din system tray nu mai are loading.
Pasul 1 — Descărcare cod sursă
Rulează în terminal (CMD sau PowerShell):

git clone https://github.com/iuliuAlexB/FlexMES.git
cd FlexMES
Pasul 2 — Build și pornire
Prima rulare durează aproximativ 3 minute:

docker compose up --build

Aplicația este gată când apare în terminal:

INFO: Application startup complete
Pasul 3 — Accesare
Deschide browserul la:

http://localhost:8000
Credențiale demo

Utilizator	Parolă	Rol
admin	admin123	Manager — acces complet
operator1	op123	Operator — Panou QC S4
Oprire
docker compose down

