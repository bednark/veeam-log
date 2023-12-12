import os, smtplib, ssl, paramiko, time
from email.message import EmailMessage
from datetime import date
from getpass import getpass

hosts = ['192.168.1.10'] # List of hosts to check

mail_content = '''
<html>
<style>
table { width: 50%; text-align: center; }
table, th, td { border:1px solid black; border-collapse: collapse }
</style>
<table>
<tr><td>Nazwa klienta</td><td>Job</td><td>Status</td></tr>
'''

session_day = date.today().strftime("%Y%m%d")

for hostname in hosts:
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname, 22, "serwis", key_filename="/root/.ssh/linux_key")

        stdin, stdout, stderr = client.exec_command(f'sudo ls /var/log/veeam/Backup')
        jobs = stdout.readlines()

        for job in jobs:
            stdin, stdout, stderr = client.exec_command(f'sudo ls /var/log/veeam/Backup/{job[:-1]} | grep Session_{session_day}_*')
            time.sleep(0.1)
            session = stdout.readline()[:-1]

            client.exec_command(f"sudo cp -f /var/log/veeam/Backup/{job[:-1]}/{session}/Job.log ./{job[:-1]}-{session_day}.log")
            client.exec_command(f"sudo chown serwis:serwis ./{job[:-1]}-{session_day}.log")

            if os.path.exists(f"./{job[:-1]}-{session_day}"):
                os.system(f"rm {job[:-1]}-{session_day}")

            os.system(f"scp -i /root/.ssh/linux_key -o ConnectTimeout=15 -o StrictHostKeyChecking=no serwis@{hostname}:{job[:-1]}-{session_day}.log ./")
            client.exec_command(f"rm -rf ./{job[:-1]}-{session_day}.log")

            mail_content += f"<tr><td>{hostname.split('.')[1].capitalize()}</td><td>{job}</td>"

            if not os.path.exists(f"./{job[:-1]}-{session_day}.log"):
                mail_content += '<td style="background-color: red;">FAILED</td></tr>\n'
                continue

            with open(f"{job[:-1]}-{session_day}.log", "r", encoding="utf-8") as log:
                job_status = log.readlines()

            if "JOB STATUS: SUCCESS" in job_status[len(job_status) - 3]:
                mail_content += '<td style="background-color: green;">SUCCESS</td></tr>\n'
            else:
                mail_content += '<td style="background-color: red;">FAILED</td></tr>\n'

            os.system(f"rm {job[:-1]}-{session_day}.log")

        client.close()
    except:
        mail_content += f'<tr><td>{hostname.split(".")[1].capitalize()}</td><td></td><td style="background-color: red;">NOT CONNECTED</td></tr>' + "\n"

mail_content += '''</table>
</html>
'''

sender = "sender@example.com" # Sender email
receiver = "receiver@example.com" # Receiver email
passwd = getpass("Input password: ")

mail_msg = EmailMessage()
mail_msg["From"] = sender
mail_msg["To"] = receiver
mail_msg["Subject"] = f"VEEAM BACKUP LINUX AGENT {session_day}"
mail_msg.set_content(mail_content, subtype="html")

context = ssl.create_default_context()

print("Sending log!")

srv = smtplib.SMTP("smtp.example.com", 587) # SMTP server settings
srv.ehlo()
srv.starttls(context=context)
srv.ehlo()
srv.login(sender, passwd)
srv.send_message(mail_msg)
srv.quit()

print("Success!")