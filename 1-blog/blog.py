from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from functools import wraps #Decoratorlar için kullanılan bir yapı

# Kullanıcı Giriş Decorator'ı
def login_required(f): #İçerisine dashboard() fonksiyonumuz geliyor
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if "logged_in" in session:
            return f(*args, **kwargs)#kullanıcı girişi varsa dashboard() fonksiyonunu çalıştır.
        else:
            flash("Bu sayfayı görüntülemek için lütfen giriş yapın.","danger")
            return redirect(url_for("login"))

    return decorated_function

# Kullanıcı Kayıt Formu 
class RegisterForm(Form):
    name = StringField("İsim Soyisim",validators=[validators.Length(min = 4,max = 25)])
    username = StringField("Kullanıcı Adı",validators=[validators.Length(min = 5,max = 35)])
    email = StringField("Email Adresi",validators=[validators.Email(message = "Lütfen Geçerli Bir Email Adresi Girin...")])
    password = PasswordField("Parola:",validators=[
        validators.DataRequired(message = "Lütfen bir parola belirleyin"),
        validators.EqualTo(fieldname = "confirm",message="Parolanız Uyuşmuyor...")
    ])
    confirm = PasswordField("Parola Doğrula")

# Makale Formu 
class ArticleForm(Form): #username bilgisini session'lardan alabildiğim için burada vermeye gerek yok.
    title = StringField("Makale Başlığı",validators=[validators.Length(min = 5,max = 100)]) 
    content = TextAreaField("Makale İçeriği",validators=[validators.Length(min = 10)])

# Kullanıcı Giriş Formu
class LoginForm(Form):
    username = StringField("Kullanıcı Adı")
    password = PasswordField("Parola")


app = Flask(__name__)

app.secret_key= "hablog" #flash mesajlarının yayınlanabilmesi için, uygulamamızım "secret key"inin olması gerekir.

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_PORT"] = 3306
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = "mysql1234"
app.config["MYSQL_DB"] = "hablog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor" #Aldığımız veriler sözlük olarak geliyor.

mysql = MySQL(app)

###########################REQUEST'ler için RESPONSE döndürecek decorator'lar###########################

#Ana Sayfa REQUEST
@app.route("/")
def index():
   return render_template("index.html")

#Hakkında REQUEST
@app.route("/about")
def about():
    return render_template("about.html")

#Kayıt Olma REQUEST
@app.route("/register",methods = ["GET","POST"]) 
def register():
    form = RegisterForm(request.form)

    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()

        sorgu = "Insert into users(name,email,username,password) VALUES(%s,%s,%s,%s)"

        cursor.execute(sorgu,(name,email,username,password))
        mysql.connection.commit() #db.SaveChanges()

        cursor.close()
        flash("Başarıyla Kayıt Oldunuz...","success")
        return redirect(url_for("login"))
    else:
        return render_template("register.html",form = form)

# Login İşlemi REQUEST
@app.route("/login",methods =["GET","POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST": 
       username = form.username.data
       password_entered = form.password.data

       cursor = mysql.connection.cursor()

       sorgu = "Select * From users where username = %s"

       result = cursor.execute(sorgu,(username,))

       if result > 0: #boyle bir kullanici olmayabilir.

           data = cursor.fetchone()#veritabanındaki veriyi/verileri almayı sağlayan metod. => verimiz/verilerimiz sözlük olarak gelmekte.
           real_password = data["password"]
           if sha256_crypt.verify(password_entered, real_password):
               flash("Başarıyla Giriş Yaptınız...","success")

               session["logged_in"] = True #"logged_in" anahtarını vererek session'u başlatmış oluyorum
               session["username"] = username

               return redirect(url_for("index"))#Giriş sonrası anasayfaya dön.
           else:
               flash("Parolanızı Yanlış Girdiniz...","danger")
               return redirect(url_for("login"))#Tekrardan login sayfasına yönlen.

       else:
           flash("Böyle bir kullanıcı bulunmuyor...","danger")
           return redirect(url_for("login"))#Tekrardan login sayfasına yönlen.

    
    return render_template("login.html",form = form)

#Kontrol Paneli REQUEST
@app.route("/dashboard")
@login_required #kullanıcı girişi varsa bu fonksiyonun çalıştırılmasını sağlayacak Decorator.
def dashboard():

    #Kendi makalelerimi kontrol panelimde gösterme
    cursor = mysql.connection.cursor()

    sorgu = "Select * From articles where author = %s"

    result = cursor.execute(sorgu,(session["username"],))

    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html",articles = articles) #Hoşgeldin user yazısı => dashboard.html'de.
    else:
        return render_template("dashboard.html")

# Logout İşlemi REQUEST
@app.route("/logout")
def logout():
    session.clear() #session'u sil.
    return redirect(url_for("index")) #anasaydaya yönlendir.

# Makale Sayfası REQUEST
@app.route("/articles") #Bütün makaleleri getir.
def articles():
    cursor = mysql.connection.cursor()

    sorgu = "Select * From articles"

    result = cursor.execute(sorgu)

    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html", articles = articles)
    else:
        return render_template("articles.html")

# Makale Ekleme REQUEST
@app.route("/addarticle",methods = ["GET","POST"])
def addarticle():
    form = ArticleForm(request.form) #Oluşturduğumuz makale formunu içerisine veriyoruz.
    if request.method == "POST" and form.validate():#sıkıntısız bir yerleştirme olduğunu form.validate() ile doğruluyorum
        title = form.title.data
        content = form.content.data
        #username bilgimi session'dan alıcam

        cursor = mysql.connection.cursor()

        sorgu = "Insert into articles(title,author,content) VALUES(%s,%s,%s)"

        cursor.execute(sorgu,(title,session["username"],content))

        mysql.connection.commit()#db.SaveChanges();

        cursor.close()#using()

        flash("Makale Başarıyla Eklendi","success")

        return redirect(url_for("dashboard"))

    return render_template("addarticle.html",form = form) # get request atınca sadece formu ver.

#Makale Silme REQUEST => Giriş yapmayanı ve başkasının makalesini silmek isteyeni engelle!
@app.route("/delete/<string:id>")#dinamik URL yapısı
@login_required #Kullanıcı girşini kontrol eden decorator'umuz => kullanıcı girişi yapmadan yapamıyoruz zaten.
def delete(id):
    cursor = mysql.connection.cursor()

    sorgu = "Select * from articles where author = %s and id = %s" #bana ait böyle bir makale var mı? => /delete/99999 URL kısmından verilebilir.

    result = cursor.execute(sorgu,(session["username"],id))

    if result > 0:
        sorgu2 = "Delete from articles where id = %s" #bana ait böyle bir makale varmış. Bunu makale tablosundan çıkar.

        cursor.execute(sorgu2,(id,))

        mysql.connection.commit() #db.SaveChanges()

        return redirect(url_for("dashboard"))

    else:
        flash("Böyle bir makale yok veya bu işleme yetkiniz yok","danger")
        return redirect(url_for("index"))

#Makale Güncelleme REQUEST
@app.route("/edit/<string:id>",methods = ["GET","POST"])#dinamik URL yapısı | Bu kısımda da formlarımız olacağı için GET VE POST metodlarını alabileceğini belirtiyoruz.
@login_required #Kullanıcı girşini kontrol eden decorator'umuz => kullanıcı girişi yapmadan yapamıyoruz zaten.
def update(id):
   if request.method == "GET":
       cursor = mysql.connection.cursor()

       sorgu = "Select * from articles where id = %s and author = %s" #bana ait böyle bir makale var mı? => /update/99999 URL | kısmından verilebilir.
       result = cursor.execute(sorgu,(id,session["username"]))

       if result == 0:
           flash("Böyle bir makale yok veya bu işleme yetkiniz yok","danger")
           return redirect(url_for("index"))

       else:
           article = cursor.fetchone()
           form = ArticleForm() #form'u göstermem gerekiyor. => ArticleForm'umuzu request.form ile oluşturuyorduk ama burada içerisine vt'den gelen değerleri atacağım için bu şekilde

           form.title.data = article["title"]
           form.content.data = article["content"]
           return render_template("update.html",form = form)

   else:
       # POST REQUEST => Güncelleme kısmında işlemlerimi hallettim.
       form = ArticleForm(request.form)

       newTitle = form.title.data
       newContent = form.content.data

       sorgu2 = "Update articles Set title = %s,content = %s where id = %s "

       cursor = mysql.connection.cursor()

       cursor.execute(sorgu2,(newTitle,newContent,id))

       mysql.connection.commit()#db.saveChanges()

       flash("Makale başarıyla güncellendi","success")

       return redirect(url_for("dashboard"))

       pass

# Makale Detay Sayfası REQUEST
@app.route("/article/<string:id>")#dinamik URL çekiyor.
def article(id):
    cursor = mysql.connection.cursor()
    
    sorgu = "Select * from articles where id = %s"

    result = cursor.execute(sorgu,(id,))

    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html",article = article)
    else:
        return render_template("article.html")

# Arama URL REQUEST => articles.html
@app.route("/search",methods = ["GET","POST"])
def search():
   if request.method == "GET":          #URL kısmından .../search girersen anasayfaya atıyor. Burada amaç search kutusuna bir şey yazdırmadan search kısmına gitmeni engellemek
       return redirect(url_for("index"))

   else:
       keyword = request.form.get("keyword") #html'de input alanımızın name kısmı "keyword"

       cursor = mysql.connection.cursor()

       sorgu = "Select * from articles where title like '%" + keyword +"%'"

       result = cursor.execute(sorgu)

       if result == 0:
           flash("Aranan kelimeye uygun makale bulunamadı...","warning")
           return redirect(url_for("articles"))

       else:
           articles = cursor.fetchall()#içerisinde "keyword" umuzun geçtiği article başlıkları

           return render_template("articles.html",articles = articles)

if __name__ == "__main__":
    app.run(debug=True) #debug=True => Kaydedildiğinde otomatik olarak işlemler işlensin.

