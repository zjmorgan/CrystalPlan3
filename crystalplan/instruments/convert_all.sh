echo "This script converts all XLS file in the folder to CSV files."
for myfile in ./*.csv
do
filename=$(basename $myfile)
extension=${filename##*.}
filename=${filename%.*}
echo "Converting $filename"
ssconvert "$filename.xls" "$filename.csv"
done
