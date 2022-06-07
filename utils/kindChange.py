from django.contrib.auth.decorators import login_required

class KindChangeFunction(object):
    @classmethod
    def kindChange1(self, flag, name):
        if flag=='on':
            return name
        else:
            return "None"
