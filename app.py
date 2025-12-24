from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///diabetes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class PenderitaDM(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kode_provinsi = db.Column(db.Integer, nullable=False)
    nama_provinsi = db.Column(db.String(100), nullable=False)
    kode_kabupaten_kota = db.Column(db.Integer, nullable=False)
    nama_kabupaten_kota = db.Column(db.String(100), nullable=False)
    jumlah_penderita_dm = db.Column(db.Integer, nullable=False)
    satuan = db.Column(db.String(50), nullable=False)
    tahun = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<PenderitaDM {self.nama_kabupaten_kota}>'

import csv
import os

with app.app_context():
    db.create_all()
    
    # Check if data exists, if not, seed from CSV
    if not PenderitaDM.query.first():
        print("Seeding database from diabetes.csv...")
        csv_path = os.path.join(app.root_path, 'diabetes.csv')
        if os.path.exists(csv_path):
            with open(csv_path, mode='r', encoding='utf-8') as csv_file:
                csv_reader = csv.DictReader(csv_file)
                for row in csv_reader:
                    # Check if record already exists to avoid duplicates (optional, but good practice if not checking empty table)
                    # Here we just blindly add because we checked the table is empty
                    new_record = PenderitaDM(
                        # id=int(row['id']), # Let database handle ID auto-increment or use CSV ID if preferred. 
                        # Using CSV ID might be risky if they duplicate or gap, but let's stick to auto-increment for safety unless forced.
                        # Actually, looking at the CSV, ID is sequential. Let's strictly follow the CSV content.
                        id=int(row['id']),
                        kode_provinsi=int(row['kode_provinsi']),
                        nama_provinsi=row['nama_provinsi'],
                        kode_kabupaten_kota=int(row['kode_kabupaten_kota']),
                        nama_kabupaten_kota=row['nama_kabupaten_kota'],
                        jumlah_penderita_dm=int(row['jumlah_penderita_dm']),
                        satuan=row['satuan'],
                        tahun=int(row['tahun'])
                    )
                    db.session.add(new_record)
                db.session.commit()
            print("Database seeded successfully!")
        else:
            print("diabetes.csv not found, skipping seed.")


from sqlalchemy import func

@app.route('/')
def home():
    # Comprehensive Data Stats
    total_cases = db.session.query(func.sum(PenderitaDM.jumlah_penderita_dm)).scalar() or 0
    total_records = PenderitaDM.query.count()
    
    # Trend Analysis Stats
    min_year = db.session.query(func.min(PenderitaDM.tahun)).scalar()
    max_year = db.session.query(func.max(PenderitaDM.tahun)).scalar()
    
    # Regional Focus Stats
    # Count unique kabupaten/kota
    unique_regions = db.session.query(PenderitaDM.nama_kabupaten_kota).distinct().count()
    
    stats = {
        'total_cases': total_cases,
        'total_records': total_records,
        'min_year': min_year,
        'max_year': max_year,
        'unique_regions': unique_regions
    }
    
    return render_template('index.html', stats=stats)

@app.route('/trend')
def trend():
    # Yearly Trend Data
    yearly_data = db.session.query(PenderitaDM.tahun, func.sum(PenderitaDM.jumlah_penderita_dm)).group_by(PenderitaDM.tahun).order_by(PenderitaDM.tahun).all()
    years = [row[0] for row in yearly_data]
    cases_per_year = [row[1] for row in yearly_data]
    return render_template('trend.html', years=years, cases_per_year=cases_per_year)

@app.route('/regional')
def regional():
    # Top 10 Regions
    top_regions_query = db.session.query(PenderitaDM.nama_kabupaten_kota, func.sum(PenderitaDM.jumlah_penderita_dm)).group_by(PenderitaDM.nama_kabupaten_kota).order_by(func.sum(PenderitaDM.jumlah_penderita_dm).desc())
    top_10 = top_regions_query.limit(10).all()
    region_names = [row[0] for row in top_10]
    region_totals = [row[1] for row in top_10]
    
    # Pie Chart Data: Top 5 Regions vs Others
    top_5 = top_regions_query.limit(5).all()
    top_5_names = [row[0] for row in top_5]
    top_5_totals = [row[1] for row in top_5]
    
    total_all_cases = db.session.query(func.sum(PenderitaDM.jumlah_penderita_dm)).scalar() or 0
    total_top_5 = sum(top_5_totals)
    others_total = total_all_cases - total_top_5
    
    pie_labels = top_5_names + ['OTHERS']
    pie_data = top_5_totals + [others_total]
    
    return render_template('regional.html', region_names=region_names, region_totals=region_totals, pie_labels=pie_labels, pie_data=pie_data)

@app.route('/dashboard')
def dashboard():
    search_query = request.args.get('q', '')
    year_filter = request.args.get('year', '')
    
    query = PenderitaDM.query
    
    if search_query:
        query = query.filter(PenderitaDM.nama_kabupaten_kota.ilike(f'%{search_query}%'))
    
    if year_filter:
        query = query.filter(PenderitaDM.tahun == year_filter)
        
    data = query.all()
    
    # Get unique years for the filter dropdown
    available_years = db.session.query(PenderitaDM.tahun).distinct().order_by(PenderitaDM.tahun.desc()).all()
    available_years = [r[0] for r in available_years]
    
    return render_template('list.html', data=data, current_search=search_query, current_year=year_filter, years=available_years)

@app.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        new_data = PenderitaDM(
            kode_provinsi=request.form['kode_provinsi'],
            nama_provinsi=request.form['nama_provinsi'],
            kode_kabupaten_kota=request.form['kode_kabupaten_kota'],
            nama_kabupaten_kota=request.form['nama_kabupaten_kota'],
            jumlah_penderita_dm=request.form['jumlah_penderita_dm'],
            satuan=request.form['satuan'],
            tahun=request.form['tahun']
        )
        db.session.add(new_data)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('form.html', action='Add')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    data = PenderitaDM.query.get_or_404(id)
    if request.method == 'POST':
        data.kode_provinsi = request.form['kode_provinsi']
        data.nama_provinsi = request.form['nama_provinsi']
        data.kode_kabupaten_kota = request.form['kode_kabupaten_kota']
        data.nama_kabupaten_kota = request.form['nama_kabupaten_kota']
        data.jumlah_penderita_dm = request.form['jumlah_penderita_dm']
        data.satuan = request.form['satuan']
        data.tahun = request.form['tahun']
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('form.html', action='Edit', data=data)

@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    data = PenderitaDM.query.get_or_404(id)
    db.session.delete(data)
    db.session.commit()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)