source .venv/bin/activate
gunicorn server.server:app --bind 0.0.0.0:5000


# Enable and start service
-- Reload systemd to read the new service file
sudo systemctl daemon-reload

-- Enable the service to start on boot
sudo systemctl enable gunicorn

sudo systemctl start gunicorn
sudo systemctl status gunicorn


# view logs
sudo journalctl -u gunicorn -f



# cp service file to
/etc/systemd/system/


# For raspberry pi
- To disable the desktop and windows manager:
``` shell
    sudo systemctl set-default multi-user.target
```

- To re-enable
``` shell
    sudo systemctl set-default graphical.target
```


For both reboot for it to take effect