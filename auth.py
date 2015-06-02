# -*- coding: utf-8 -*-

def login_required(handler_method):
    def check_login(self, *args, **kwargs):
        if not 'username' in self.session:
            return self.redirect("/user/login")
        else:
            handler_method(self, *args, **kwargs)

    return check_login


def admin_required(handler_method):
    def check_admin(self, *args, **kwargs):
        if (not 'username' in self.session) or (not 'usertype' in self.session) or self.session['usertype']!="Admin" :
            return self.redirect("/user/login")
        else:
            handler_method(self, *args, **kwargs)

    return check_admin
