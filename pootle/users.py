#!/usr/bin/env python

from jToolkit.web import server
from jToolkit.web import session
from jToolkit.widgets import widgets
from jToolkit.widgets import form
from jToolkit import mailer
from translate.pootle import pagelayout

class RegistrationError(ValueError):
  pass

class LoginPage(server.LoginPage, pagelayout.PootlePage):
  """wraps the normal login page in a PootlePage layout"""
  def __init__(self, session, extraargs={}, confirmlogin=0, specialmessage=None, languagenames=None):
    server.LoginPage.__init__(self, session, extraargs, confirmlogin, specialmessage, languagenames)
    contents = pagelayout.IntroText(self.contents)
    pagelayout.PootlePage.__init__(self, session.localize("Login to Pootle"), contents, session)

  def getcontents(self):
    return pagelayout.PootlePage.getcontents(self)

class RegisterPage(pagelayout.PootlePage):
  """page for new registrations"""
  def __init__(self, session, argdict):
    self.localize = session.localize
    introtext = [pagelayout.IntroText(self.localize("Please enter your registration details"))]
    if session.status:
      statustext = pagelayout.IntroText(session.status)
      introtext.append(statustext)
    self.argdict = argdict
    contents = [introtext, self.getform()]
    pagelayout.PootlePage.__init__(self, self.localize("Pootle Registration"), contents, session)

  def getform(self):
    columnlist = [("email", self.localize("Email Address"), self.localize("Must be a valid email address")),
                  ("username", self.localize("Username"), self.localize("Your requested username")),
                  ("password", self.localize("Password"), self.localize("Your desired password"))]
    formlayout = {1:("email", ), 2:("username", ), 3:("password", )}
    extrawidgets = [widgets.Input({'type': 'submit', 'name':'register', 'value':self.localize('Register')})]
    record = dict([(column[0], self.argdict.get(column[0], "")) for column in columnlist])
    return form.SimpleForm(record, "register", columnlist, formlayout, {}, extrawidgets)

class ActivatePage(pagelayout.PootlePage):
  """page for new registrations"""
  def __init__(self, session, argdict):
    self.localize = session.localize
    introtext = [pagelayout.IntroText(self.localize("Please enter your activation details"))]
    if session.status:
      statustext = pagelayout.IntroText(session.status)
      introtext.append(statustext)
    self.argdict = argdict
    contents = [introtext, self.getform()]
    pagelayout.PootlePage.__init__(self, self.localize("Pootle Account Activation"), contents, session)

  def getform(self):
    columnlist = [("username", self.localize("Username"), self.localize("Your requested username")),
                  ("activationcode", self.localize("Activation Code"), self.localize("The activation code you received"))]
    formlayout = {1:("username", ), 2:("activationcode", )}
    extrawidgets = [widgets.Input({'type': 'submit', 'name':'activate', 'value':self.localize('Activate Account')})]
    record = dict([(column[0], self.argdict.get(column[0], "")) for column in columnlist])
    return form.SimpleForm(record, "activate", columnlist, formlayout, {}, extrawidgets)

class OptionalLoginAppServer(server.LoginAppServer):
  """a server that enables login but doesn't require it except for specified pages"""
  def handle(self, req, pathwords, argdict):
    """handles the request and returns a page object in response"""
    argdict = self.processargs(argdict)
    session = self.getsession(req, argdict)
    if session.isopen:
      session.pagecount += 1
      session.remote_ip = self.getremoteip(req)
    return self.getpage(pathwords, session, argdict)

  def handleregistration(self, session, argdict):
    """handles the actual registration"""
    supportaddress = getattr(self.instance.registration, 'supportaddress', "")
    username = argdict.get("username", "")
    if not username or not username.isalnum() or not username[0].isalpha():
      raise RegistrationError("Username must be alphanumeric, and must start with an alphabetic character")
    email = argdict.get("email", "")
    password = argdict.get("password", "")
    if not (email and "@" in email and "." in email):
      raise RegistrationError("You must supply a valid email address")
    userexists = session.loginchecker.userexists(username)
    if userexists:
      usernode = getattr(session.loginchecker.users, username)
      # use the email address on file
      email = getattr(usernode, "email", email)
      password = ""
      # TODO: we can't figure out the password as we only store the md5sum. have a password reset mechanism
      message = "You (or someone else) attempted to register an account with your username.\n"
      message += "We don't store your actual password but only a hash of it\n"
      if supportaddress:
        message += "If you have a problem with registration, please contact %s\n" % supportaddress
      else:
        message += "If you have a problem with registration, please contact the site administrator\n"
      displaymessage = "That username already exists. An email will be sent to the registered email address...\n"
      redirecturl = "login.html?username=%s" % username
      displaymessage += "Proceeding to <a href='%s'>login</a>\n" % redirecturl
    else:
      minpasswordlen = 6
      if not password or len(password) < minpasswordlen:
        raise RegistrationError("You must supply a valid password of at least %d characters" % minpasswordlen)
      setattr(session.loginchecker.users, username + ".email", email)
      setattr(session.loginchecker.users, username + ".passwdhash", session.md5hexdigest(password))
      setattr(session.loginchecker.users, username + ".activated", 0)
      activationcode = self.generateactivationcode()
      setattr(session.loginchecker.users, username + ".activationcode", activationcode)
      activationlink = ""
      message = "A Pootle account has been created for you using this email address\n"
      if session.instance.baseurl.startswith("http://"):
        message += "To activate your account, follow this link:\n"
        activationlink = session.instance.baseurl
        if not activationlink.endswith("/"):
          activationlink += "/"
        activationlink += "activate.html?username=%s&activationcode=%s" % (username, activationcode)
        message += "  %s  \n" % activationlink
      message += "Your activation code is:\n%s\n" % activationcode
      if activationlink:
        message += "If you are unable to follow the link, please enter the above code at the activation page\n"
      message += "This message is sent to verify that the email address is in fact correct. If you did not want to register an account, you may simply ignore the message.\n"
      redirecturl = "activate.html?username=%s" % username
      displaymessage = "Account created. You will be emailed login details and an activation code. Please enter your activation code on the <a href='%s'>activation page</a>. " % redirecturl
      if activationlink:
        displaymessage += "(Or simply click on the activation link in the email)"
    session.saveprefs()
    message += "Your user name is: %s\n" % username
    if password.strip():
      message += "Your password is: %s\n" % password
    message += "Your registered email address is: %s\n" % email
    smtpserver = self.instance.registration.smtpserver
    fromaddress = self.instance.registration.fromaddress
    messagedict = {"from": fromaddress, "to": [email], "subject": "Pootle Registration", "body": message}
    if supportaddress:
      messagedict["reply-to"] = supportaddress
    fullmessage = mailer.makemessage(messagedict)
    errmsg = mailer.dosendmessage(fromemail=self.instance.registration.fromaddress, recipientemails=[email], message=fullmessage, smtpserver=smtpserver)
    if errmsg:
      raise RegistrationError("Error sending mail: %s" % errmsg)
    return displaymessage, redirecturl

  def registerpage(self, session, argdict):
    """handle registration or return the Register page"""
    if "username" in argdict:
      try:
        displaymessage, redirecturl = self.handleregistration(session, argdict)
      except RegistrationError, message:
        session.status = str(message)
        return RegisterPage(session, argdict)
      message = pagelayout.IntroText(displaymessage)
      redirectpage = pagelayout.PootlePage("Redirecting...", [message], session)
      redirectpage.attribs["refresh"] = 10
      redirectpage.attribs["refreshurl"] = redirecturl
      return redirectpage
    else:
      return RegisterPage(session, argdict)

  def activatepage(self, session, argdict):
    """handle activation or return the Register page"""
    if "username" in argdict and "activationcode" in argdict:
      username = argdict["username"]
      activationcode = argdict["activationcode"]
      usernode = getattr(session.loginchecker.users, username, None)
      if usernode is not None:
        correctcode = getattr(usernode, "activationcode", "")
        if correctcode and correctcode.strip().lower() == activationcode.strip().lower():
          setattr(usernode, "activated", 1)
          session.saveprefs()
          redirecttext = pagelayout.IntroText("Your account has been activated! Redirecting to login...")
          redirectpage = pagelayout.PootlePage("Redirecting to login...", redirecttext, session)
          redirectpage.attribs["refresh"] = 10
          redirectpage.attribs["refreshurl"] = "login.html?username=%s" % username
          return redirectpage
      failedtext = pagelayout.IntroText("The activation link you have entered was not valid")
      failedpage = pagelayout.PootlePage("Activation Failed", failedtext, session)
      return failedpage
    else:
      return ActivatePage(session, argdict)

class PootleSession(session.LoginSession):
  """a session object that knows about Pootle"""
  def __init__(self, sessioncache, server, sessionstring = None, loginchecker = None):
    """sets up the session and remembers the users prefs"""
    super(PootleSession, self).__init__(sessioncache, server, sessionstring, loginchecker)
    self.prefs = getattr(self.loginchecker.users, self.username)

  def validate(self):
    """checks if this session is valid (which means the user must be activated)"""
    if not super(PootleSession, self).validate():
      return False
    if not getattr(getattr(self.loginchecker.users, self.username, None), "activated", 0):
      self.isvalid = False
      self.status = "username has not yet been activated"
    return self.isvalid

  def setoptions(self, argdict):
    """sets the user options"""
    userprojects = argdict.get("projects", [])
    if isinstance(userprojects, (str, unicode)):
      userprojects = [userprojects]
    setattr(self.prefs, "projects", ",".join(userprojects))
    userlanguages = argdict.get("languages", [])
    if isinstance(userlanguages, (str, unicode)):
      userlanguages = [userlanguages]
    setattr(self.prefs, "languages", ",".join(userlanguages))
    self.saveprefs()

  def getprojects(self):
    """gets the user's projects"""
    userprojects = getattr(self.prefs, "projects", "")
    return userprojects.split(",")

  def getlanguages(self):
    """gets the user's languages"""
    userlanguages = getattr(self.prefs, "languages", "")
    return userlanguages.split(",")

  def getrights(self):
    """gets the user's rights"""
    return getattr(self.prefs, "rights", None)

  def saveprefs(self):
    """saves changed preferences back to disk"""
    # TODO: this is a hack, fix it up nicely :-)
    prefsfile = self.loginchecker.users.__root__.__dict__["_setvalue"].im_self
    prefsfile.savefile()

