import smtplib
import time
from email.message import EmailMessage

# =========================
# CONFIGURACIÓN
# =========================

EMISOR = "mitnickk42@gmail.com"

# IMPORTANTE:
# Usa una contraseña de aplicación NUEVA.
# La anterior debes revocarla porque fue expuesta.
PASSWORD_APP = "kmke tszm ivly azvp"

RECEPTOR = "kiksss2021@gmail.com"

# AQUÍ DECIDES CUÁNTOS CORREOS ENVIAR
CANTIDAD = 1

# Segundos de espera entre cada correo
ESPERA = 2


# =========================
# CONEXIÓN
# =========================

try:

    print("🔄 Conectando con Gmail...")

    with smtplib.SMTP_SSL(
        "smtp.gmail.com",
        465,
        timeout=30
    ) as servidor:

        print("🔐 Iniciando sesión...")

        servidor.login(
            EMISOR,
            PASSWORD_APP
        )

        print("✅ Login correcto")
        print(f"📧 Receptor: {RECEPTOR}")
        print(f"📨 Cantidad: {CANTIDAD}")
        print("=" * 50)

        # =========================
        # ENVÍO
        # =========================

        for i in range(1, CANTIDAD + 1):

            mensaje = EmailMessage()

            mensaje["From"] = (
                f"Security Operations Center <{EMISOR}>"
            )

            mensaje["To"] = RECEPTOR

            mensaje["Subject"] = (
                f"CRITICAL SECURITY ALERT — "
                f"SQL Injection Attack Detected [{i}]"
            )

            # =========================
            # VERSIÓN TEXTO
            # =========================

            mensaje.set_content(f"""
CRITICAL SECURITY ALERT

Our security monitoring system has detected suspicious activity
targeting your server.

Threat detected: SQL Injection Attack
Severity: CRITICAL
Status: ACTIVE
Target: Database Server

Alert ID: SECURITY-{i:04d}

Multiple unauthorized database queries have been detected.

Potential consequences:

- Unauthorized access to database records
- Exposure of sensitive information
- Modification or deletion of stored data
- Compromise of administrator accounts
- Complete database takeover

Immediate investigation is recommended.

This message is part of an authorized security simulation.
""")


            # =========================
            # VERSIÓN HTML
            # =========================

            mensaje.add_alternative(f"""
<html>

<body style="
    font-family: Arial, sans-serif;
    background:#111;
    padding:30px;
">

<div style="
    max-width:650px;
    margin:auto;
    background:#1b1b1b;
    color:white;
    padding:30px;
    border:1px solid #ff3b30;
    border-radius:8px;
">

<h1 style="color:#ff3b30;">
⚠ CRITICAL SECURITY ALERT
</h1>

<h2>
SQL Injection Attack Detected
</h2>

<p>
Our security monitoring system has detected
suspicious activity targeting your server.
</p>

<hr style="border-color:#444;">

<p>
<strong>Threat:</strong>
SQL Injection Attack
</p>

<p>
<strong>Severity:</strong>
<span style="color:#ff3b30;">
CRITICAL
</span>
</p>

<p>
<strong>Status:</strong>
ACTIVE
</p>

<p>
<strong>Target:</strong>
Database Server
</p>

<p>
<strong>Alert ID:</strong>
SECURITY-{i:04d}
</p>

<hr style="border-color:#444;">

<p>
Multiple unauthorized database queries
have been detected.
</p>

<p>
The requests appear consistent with an
attempted SQL injection attack.
</p>

<p>
<strong>Potential impact:</strong>
</p>

<ul>

<li>
Unauthorized access to database records
</li>

<li>
Exposure of sensitive information
</li>

<li>
Modification or deletion of stored data
</li>

<li>
Compromise of administrator accounts
</li>

<li>
Database takeover
</li>

</ul>

<div style="
    background:#3a1111;
    padding:15px;
    border-left:5px solid #ff3b30;
    margin-top:20px;
">

<strong>
IMMEDIATE INVESTIGATION RECOMMENDED
</strong>

</div>

<br>

<p style="
    font-size:12px;
    color:#aaa;
">

Authorized security simulation —
no real attack has occurred.

</p>

</div>

</body>

</html>
""", subtype="html")


            # =========================
            # ENVIAR
            # =========================

            try:

                resultado = servidor.send_message(mensaje)

                if resultado == {}:

                    print(
                        f"✅ Enviado "
                        f"{i}/{CANTIDAD} "
                        f"→ {RECEPTOR}"
                    )

                else:

                    print(
                        f"❌ Rechazado "
                        f"{i}/{CANTIDAD}: "
                        f"{resultado}"
                    )

            except Exception as error:

                print(
                    f"❌ Error enviando "
                    f"{i}/{CANTIDAD}: {error}"
                )

            # Pausa para no enviarlos todos simultáneamente
            if i < CANTIDAD:
                time.sleep(ESPERA)


        print("=" * 50)
        print(
            f"🏁 Proceso terminado. "
            f"Se intentaron enviar {CANTIDAD} correos."
        )


# =========================
# ERRORES GENERALES
# =========================

except smtplib.SMTPAuthenticationError as error:

    print("❌ Gmail rechazó las credenciales.")
    print("Utiliza una contraseña de aplicación.")
    print(error)


except smtplib.SMTPConnectError as error:

    print("❌ No se pudo conectar con Gmail.")
    print(error)


except TimeoutError as error:

    print("❌ La conexión con Gmail expiró.")
    print(error)


except Exception as error:

    print("❌ Error inesperado:")
    print(type(error).__name__)
    print(error)